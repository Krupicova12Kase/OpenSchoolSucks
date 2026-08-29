###############################
# Made by Krupicova12Kase AKA Máťa
# Licensed under MIT license
# Report any bugs at https://github.com/Krupicova12Kase/OpenSchoolSucks/issues
###############################

# Imports
import traceback
from flask import Flask, flash, request, redirect, url_for, render_template, jsonify, abort, session as flask_session_custom
from flask_session import Session
import os
import requests
from ssl import get_server_certificate
from urllib.parse import urlparse, parse_qs
import urllib3
from bs4 import BeautifulSoup, diagnose
from io import StringIO
import re
import pandas as pd
from dotenv import load_dotenv
from colorama import init, Fore
from cachelib import FileSystemCache
from cert_chain_resolver.api import resolve

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

# Server side session to prevent cookies from being too big to handle
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "cachelib"
app.config["SESSION_CACHELIB"] = FileSystemCache(cache_dir="flask_session")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'cs-CZ,cs;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
}

Session(app)


# CERTIFICATES

certificate_chain = "psjg_chain.crt"
certificate_file = "custom"


def certificates() -> None:
    """Generate full certificate chain using cert_chain_resolver because is.psjg.cz sends incomplete
    """
    psjg_certificate = str(get_server_certificate(("is.psjg.cz", 443)))

    with open("certificates/psjg_half_chain.crt", "w") as f:
        f.write(psjg_certificate)

    with open("certificates/psjg_half_chain.crt", 'rb') as f1:
        fb = f1.read()
        chain = resolve(fb)

        with open("certificates/psjg_chain.crt", "w", encoding="utf-8") as f2:
            for cert in chain:
                f2.write(str(cert.export()))
    print("Obtained certificates successfully!")


path = os.path.join(os.path.dirname(__file__), "certificates", "psjg_chain.crt")
certificates()

if os.environ.get('VERIFY', 'True') == 'True':
    certificate = os.path.join(os.path.dirname(__file__), 'certificates', certificate_chain)
else:
    print(f"{Fore.RED}!! SSL Verification disabled !!{Fore.RESET}")
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    certificate = False


def delete_spaces(text: str) -> str:
    """ Deletes unnecessary spaces, tabs and newlines from text

    Args:
        text (str): Text to change

    Returns:
        str: Chnaged text
    """
    return re.sub(r'\s+', ' ', text.strip())


def csv_to_dataframe(text: str) -> pd.DataFrame:
    """Convert provided text to dataframe. Text needs to be in CSV format

    Args:
        text (str): Text to convert

    Returns:
        pd.DataFrame: pandas DataFrame
    """
    df = pd.read_csv(StringIO(text), sep=';')
    return df


def get_info(text: str) -> int:
    """Get info about student from text from is.psjg.cz. Currently returns only student id

    Args:
        text (str): raw HTML

    Returns:
        int: The student id
    """
    # Get full HTML webpage
    soup = BeautifulSoup(text, "html.parser")
    search = soup.find_all(title="Téma studentského portfolia")
    if len(search) > 1 or len(search) < 1:
        abort(500, f"Found {len(search)} student ids")

    href = search[0].a["href"]
    try:
        student_id = int(href[href.rfind("/") + 1:])
    except ValueError:
        abort(500, f"Failed to convert to integer {href[href.rfind("/") + 1:]}")

    return student_id


def get_csv_subjects(text: str, fieldnames: list) -> pd.DataFrame:
    """Get subjects from HTML of mainpage

    Args:
        text (str): raw HTML from is.psjg.cz
        fieldnames (list): List of filednames for DataFrame

    Returns:
        pd.DataFrame: Dataframe with subjects
    """
    df = pd.DataFrame(columns=fieldnames)
    soup = BeautifulSoup(text, "html.parser")
    try:
        # Find all tables in the HTML file
        for table in soup.find_all('table'):
            if table.tr.th.text == "Předmět":  # Search only for table with list of subjects
                for tr in table.find_all('tr'):  # Iterate through rows
                    sezam = []
                    # Iterate through columns
                    for i, td in enumerate(tr.find_all('td')):
                        if not td.a is None:
                            url = td.a.get("href")  # Get URL from link
                            query = urlparse(url).query
                            params = parse_qs(query)
                            subject_id = params.get('subjectId')[0]
                            sezam.append(subject_id)
                        sezam.append(delete_spaces(td.text))

                        if i == 3:
                            df.loc[len(df)] = sezam

        return df
    except Exception as e:
        print(traceback.format_exc())
        print(diagnose(soup))
        abort(500)


def get_portfolio(text: str) -> dict:
    """Gets portfolio info from HTML. for example return, see example.jsonc

    Args:
        text (str): raw HTML from is.psjg.cz/achievement

    Raises:
        Exception: _description_
        Exception: _description_
        Exception: _description_

    Returns:
        dict: Dictionary with total points, place and info about each entry
    """
    soup = BeautifulSoup(text, "html.parser")
    portfoliodict = {}
    data = []
    try:
        # dict
        for div in soup.find_all("div", class_="row_achievement"):
            subdict = {}
            total_points = 0
            tableVar = div.find_all("table")

            # Checks
            if not tableVar:
                raise Exception("Failed to find table in div")
            tbodyList = div.table.find_all("tbody")
            if len(tbodyList) >= 2 or not div.table.tbody:
                abort(500)
                raise Exception(
                    f"Failed to get tbodies. found {tbodyList.len()} total.")

            tBodyVar = tbodyList[0]

            items = []
            for tr in tBodyVar.find_all("tr"):
                tdVar = tr.find_all("td")

                # subsubdict
                subsubdict = {}
                subsubdict["name"] = delete_spaces(tdVar[0].get_text())
                subsubdict["points"] = delete_spaces(tdVar[1].get_text())
                total_points += int(delete_spaces(tdVar[1].get_text()))
                subsubdict["description"] = delete_spaces(tdVar[2].get_text())
                items.append(subsubdict)

            # Heading
            h2 = div.find("h2")
            if not h2:
                abort(500)
                raise Exception("Failed to find h2")
            name = delete_spaces(h2.get_text())

            # subdict
            if not len(items) == 0:
                subdict["name"] = name
                subdict["items"] = items
                subdict["points"] = total_points
                data.append(subdict)

        # Total points and place
        total = soup.find("div", class_="col-md-6 offset-md-3").find("div").find("h2").get_text()
        points = delete_spaces(total[total.find(": ") + 2:total.find(" b")])  # Extract points
        place = delete_spaces(total[total.find("(") + 1:total.find(". v")])  # Extract place

        try:
            points = int(points)
            place = int(place)
        except ValueError as e:
            print(f"Error converting to integer: {e}")
            abort(500)

        portfoliodict["data"] = data
        portfoliodict["points"] = points
        portfoliodict["place"] = place

    except Exception as e:
        print(traceback.format_exc())
        abort(500)
    return portfoliodict


def znamka_from_percentage(percentage) -> int | str:
    """Gets number grade from percentage. Returns 0 if percentrage is too low / too high

    Args:
        percentage (_type_): _description_

    Returns:
        int | str: Grade (-1 - 5) or "N"
    """
    if str(percentage) == "-":
        return -1
    if str(percentage) == "N":
        return "N"
    if str(percentage)[len(percentage) - 1] == "%":
        percentage = percentage[:len(percentage) - 1]
        percentage = percentage.replace(",", ".")
        percentage = float(percentage)
    if percentage >= 91:
        return 1
    elif percentage >= 80:
        return 2
    elif percentage >= 60:
        return 3
    elif percentage >= 45:
        return 4
    elif percentage >= 0:
        return 5
    else:
        return 0


def split_percentage_and_points(text: str) -> tuple[int, int]:
    """Splits percentage and points from one text (see example from comment below) into tuple

    Args:
        text (str): Text in format XX,X / XX,X (YY,YY%)

    Returns:
        tuple[int, int]: tuple with points and percentage
    """
    # '89,0 / 97,0 (91,75%)'
    points = text[:text.find("(")].strip()
    percentage = text[text.find("(") + 1:text.find(")")].strip()
    return (percentage, points)


@app.route('/', methods=["GET", "POST"])
def login():
    """Main endpoint. Handles login, getting student it, grades
    """
    try:
        session = requests.Session()
        session.verify = certificate
        # -------------------------------
        # LOGIN
        # -------------------------------
        if request.method == "GET":
            return render_template("index.html")

        if request.method == "POST":
            # Get form data
            username = request.form.get("username")
            password = request.form.get("password")
            response = session.post("https://is.psjg.cz/sign/in", data={
                "name": username,
                "password": password,
                "signIn": "Přihlásit se",
                "_do": "signInForm-submit"}, headers=headers)

            if response.status_code == 200:
                flask_session_custom["cookies"] = session.cookies.get_dict()

                if "Neplatné přihlašovací jméno nebo heslo" in response.text:
                    return render_template("index.html", error="Neplatné přihlašovací jméno nebo heslo")

                # Get subjects from HTML response and write them to CSV file
                fieldnames = ["id", "Předmět", "Bodové hodnocení", "Známka", "Výsledná známka"]  # List of column names for CSV file
                subjects = get_csv_subjects(response.text, fieldnames).values.tolist()
                print(subjects)
                flask_session_custom["subjects"] = subjects
                return redirect(url_for("home"))

            else:
                return render_template("error.html", error=f"response code {response.status_code}", traceback="")

    # Error handling
    except requests.exceptions.SSLError as e:
        print(traceback.format_exc())
        return render_template("error.html", message=f"Zkuste obnovit stránku. Použitý certifikát: {certificate_file}" if True else "Nepodařilo se najít funkční certifikát.")

    except Exception as e:
        print(traceback.format_exc())
        return render_template("error.html", message="")


@app.route('/home')
def home():
    """Home page. Displays grades and redirects to subjects. Uses data from main endpoint
    """
    try:
        # Get subjects from saved cookies
        subjects = flask_session_custom.get("subjects")
        saved_cookies = flask_session_custom.get('cookies')

        if not subjects or not saved_cookies:
            return redirect(url_for("login"))

        session = requests.Session()
        session.verify = certificate
        session.cookies.update(saved_cookies)

        # Read subjects
        studentinfo_response = session.get("https://is.psjg.cz/", headers=headers)
        if studentinfo_response.status_code == 200:
            if 'id="frm-signInForm-name"' in studentinfo_response.text:
                flask_session_custom.pop('cookies', None)  # Delete old cookies
                return redirect(url_for("login"))

            student_info = get_info(studentinfo_response.text)

        flask_session_custom["studentId"] = student_info
        responseGrid = session.get("https://is.psjg.cz",
                                   params={
                                       "studentScoreGrid-id": 1,
                                       "do": "studentScoreGrid-export"
                                   }, headers=headers)
        # Results ig
        if responseGrid.status_code == 200:
            df = csv_to_dataframe(text=responseGrid.text)
            znamky = []
            df = df.fillna("")
            csvlist = df.values.tolist()

            # Add grades to csvlist
            for row in csvlist:
                znamky.append(znamka_from_percentage(row[3]))
            df["Znamka"] = znamky
            csvlist = df.values.tolist()

            flask_session_custom["znamky"] = csvlist

            # id, název, známka, finální známka, body, procenta
            subjects_display = []

            for row in subjects:
                percentage, points = split_percentage_and_points(row[2])
                subjects_display.append([row[0], row[1], row[3], row[4], percentage, points])
                
            # Check for no grades or subjects
            if len(subjects) == 0:
                subjects.append(-1)
            if len(csvlist) == 0:
                csvlist.append(-1)

            page = request.args.get('page', 1, type=int)
            per_page = 10
            start = (page - 1) * per_page
            end = start + per_page
            total_pages = (len(csvlist) + per_page - 1) // per_page

            # Render the template
            return render_template("home.html", subjects=subjects_display, znamky=csvlist[start:end], current=page, total=total_pages)
        else:
            return render_template("error.html", error=f"response code {responseGrid.status_code}", traceback="")
    except Exception as e:
        print(traceback.format_exc())
        return render_template("error.html", message="")


@app.route('/subject/<subject_id>')
def subject(subject_id: int):
    """Get grades from specific subject

    Args:
        subject_id (int): id of the subject to display
    """
    try:
        saved_cookies = flask_session_custom.get('cookies')
        student_id = flask_session_custom.get('studentId')

        if not saved_cookies or not student_id:
            return redirect(url_for("login"))

        session = requests.Session()
        session.verify = certificate
        session.cookies.update(saved_cookies)

        response = session.get("https://is.psjg.cz/student/student-exam-overview",
                               params={
                                   "studentExamOverview-examGrid-id": "1",
                                   "studentId": student_id,
                                   "subjectId": subject_id,
                                   "do": "studentExamOverview-examGrid-export"
                               }, headers=headers)

        if response.status_code == 200:

            # Check for old cookies
            if 'id="frm-signInForm-name"' in response.text:
                flask_session_custom.pop('cookies', None)  # Delete old cookies
                return redirect(url_for("login"))

            # Save response to CSV
            df = csv_to_dataframe(text=response.text)

            znamky = []
            csvlist = df.values.tolist()

            # Add znamka to csvlist
            for x, row in enumerate(csvlist):
                znamky.append(znamka_from_percentage(row[5]))
            df["Znamka"] = znamky
            csvlist = df.values.tolist()

            # Get rid of nan values
            for x, row in enumerate(csvlist):
                for y, item in enumerate(row):
                    if pd.isna(item):
                        csvlist[x][y] = ""
            return render_template("znamka.html", znamky=csvlist)
        else:
            return render_template("error.html", error=f"Http code {response.status_code}", traceback="")

    except requests.exceptions.SSLError as e:
        print(traceback.format_exc())
        return render_template("error.html", message=f"Zkuste obnovit stránku. Použitý certifikát: {certificate_file}" if True else "Nepodařilo se najít funkční certifikát.")

    except Exception as e:
        print(traceback.format_exc())
        return render_template("error.html", message="")


@app.route('/portfolio')
def portfolio():
    """Student prtfolio endpoint
    """
    try:
        saved_cookies = flask_session_custom.get('cookies')
        student_id = flask_session_custom.get('studentId')

        if not saved_cookies or not student_id:
            return redirect(url_for("login"))
        session = requests.Session()
        session.verify = certificate
        session.cookies.update(saved_cookies)

        response = session.get(f"https://is.psjg.cz/achievement/view/{student_id}", headers=headers)

        if response.status_code == 200:
            # Check for old cookies
            if 'id="frm-signInForm-name"' in response.text:
                flask_session_custom.pop('cookies', None)  # Delete old cookies
                return redirect(url_for("login"))

            # Render the template
            return render_template("portfolio.html", portfolio=get_portfolio(text=response.text))

    except requests.exceptions.SSLError as e:
        print(traceback.format_exc())
        return render_template("error.html", message=f"Zkuste obnovit stránku. Použitý certifikát: {certificate_file}" if True else "Nepodařilo se najít funkční certifikát.")

    except Exception as e:
        print(traceback.format_exc())
        return render_template("error.html", message="")

# Zkoušení


@app.route('/zkouseni')
def zkouseni():
    try:
        student_id = flask_session_custom.get('studentId')

        # Make sure it exists
        if not student_id:
            return redirect(url_for("login"))

    except Exception as e:
        print(traceback.format_exc())
        return render_template("error.html", message="")

    # Render the template
    return render_template("zkouseni.html")


@app.route("/logout")
def logout():
    """Logout. Redirect to login
    """
    flask_session_custom.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=(os.environ.get('DEBUG') == 'True'))
