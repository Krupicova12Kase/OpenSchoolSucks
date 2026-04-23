###############################
# Made by Krupicova12Kase AKA Máťa
# Licensed under MIT license
# Report any bugs at https://github.com/Krupicova12Kase/OpenSchoolSucks/issues
###############################

#Imports
import traceback
from flask import Flask, flash, request, redirect, url_for, render_template, jsonify, session as flask_session_custom
from flask_session import Session
import os
import requests
from bs4 import BeautifulSoup, diagnose
from io import *
import re
import pandas as pd
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
from ssl import get_server_certificate

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default-hodnota')
REQUEST_NAMES = ["username","password"]

# Server side session to prevent cookies from being too big to handle
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# STUPID CERTIFICATES
def certificates() -> None:
    print("Getting certificates...")
    psjg_certificate = get_server_certificate(("is.psjg.cz", 443))
    # Open file for merging
    with open("certificates/psjg_chain.crt", "w") as f1:
        # Write first half from the website
        f1.write(psjg_certificate)
        #Write second half from file (https://letsencrypt.org/)
        with open("certificates/cert_end.pem", "r",) as f2:
            f1.write("\n")
            f1.write(f2.read())
    # Close everything
    f1.close()
    f2.close()
    print("Certificates obtained successfully!")
    return
    
certificates()
certificate = os.path.join(os.path.dirname(__file__), 'certificates', 'psjg_chain.crt')

# Deletes unnecessary spaces, tabs and newlines from text
def delete_spaces(text:str) -> str:
    return re.sub(r'\s+', ' ', text.strip())

# Saves provided string to CSV using pandas
def csv_to_dataframe(text:str) -> pd.DataFrame:
    df = pd.read_csv(StringIO(text), sep=';')
    return df

# Get info about student from HTML
def get_info(text:str) -> tuple:
    sezam = []
    # Get full HTML webpage (Kdo tohle sakra dělal, kdyby to bylo na mě, tak udělám API)
    soup = BeautifulSoup(text, "html.parser")
    for table in soup.find_all('table'): #Find all tables in the HTML file
        if table.tr.th.text == "Předmět": #Search only for table with list of subjects
            for tr in table.find_all('tr'): #Iterate through rows
                for a_tag in tr.find_all('a'): #Search through links
                    url = a_tag.get("href") #Get URL from link
                    query = urlparse(url).query
                    params = parse_qs(query)

                    student_id = params.get('studentId')[0]
                    
                    sezam.append(student_id)
            break
        
    # "Security" checks
    # Check if list isn't empty      
    if len(sezam) == 0:
        return ("ERROR",1)
    
    # Check if there aren't multiple student IDs
    studentIds = []
    for i in sezam:
        if not i[0] in studentIds:
            studentIds.append(i[0])
    if len(studentIds) > 1:
        return ("ERROR",2)
    
    return ("OK", student_id)

# Gets subjects from HTML text
def get_csv_subjects(text:str, fieldnames:list) -> pd.DataFrame:
    df = pd.DataFrame(columns=fieldnames)
    soup = BeautifulSoup(text, "html.parser")
    try:  
        for table in soup.find_all('table'): #Find all tables in the HTML file
            if table.tr.th.text == "Předmět": #Search only for table with list of subjects
                for tr in table.find_all('tr'): #Iterate through rows
                    sezam = []
                    for i,td in enumerate(tr.find_all('td')): #Iterate through columns
                        if not td.a == None:
                            url = td.a.get("href") #Get URL from link
                            query = urlparse(url).query
                            params = parse_qs(query)
                            subject_id = params.get('subjectId')[0]
                            sezam.append(subject_id)
                        sezam.append(delete_spaces(td.text))
                        
                        if i == 3:
                            df.loc[len(df)] = sezam

        return ("OK",df)
    except Exception as e:
        return ("ERROR",diagnose(soup),e)                

# Calculate grade from percentage
def znamka_from_percentage(percentage) -> int:
    if str(percentage) == "-":
        return -1
    if str(percentage)[len(percentage)-1] == "%":
        percentage = percentage[:len(percentage)-1]
        percentage = percentage.replace(",",".")
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

def split_percentage_and_points(text:str) -> tuple:
    # '89,0 / 97,0 (91,75%)'
    points = text[:text.find("(")].strip()
    percentage = text[text.find("(")+1:text.find(")")].strip()
    return (percentage, points)

@app.route('/',methods=["GET","POST"])
def func():
    try:
        session = requests.Session()
        session.verify = certificate
        # -------------------------------
        # LOGIN
        # -------------------------------
        if request.method == "GET":
            return render_template("index.html")
        
        # Handle POST request - get form data
        username = request.form.get("username")
        password = request.form.get("password")
        response = session.post("https://is.psjg.cz/sign/in", data={                                 
            "name": username,
            "password": password,
            "signIn": "Přihlásit se",
            "_do": "signInForm-submit"})
        print(response.status_code)
        flask_session_custom["cookies"] = session.cookies.get_dict()
        
        if "Neplatné přihlašovací jméno nebo heslo" in response.text:
            return render_template("index.html", error="Neplatné přihlašovací jméno nebo heslo") 
        
        # -------------------------------
        # HOMEPAGE
        # -------------------------------
        
        # Get subjects from HTML response and write them to CSV file
        fieldnames = ["id","Předmět", "Bodové hodnocení","Známka","Výsledná známka"] #List of column names for CSV file
        subjects = get_csv_subjects(response.text, fieldnames)
        if subjects[0] == "OK":
            SubjcetList = subjects[1].values.tolist()
        elif subjects[0] == "ERROR":
            print(f"{subjects[1]},\n{subjects[2]}")
            raise Exception(f"Error code: {subjects[0]}")
        
        # id, název, známka, finální známka, body, procenta
        for i in SubjcetList:
            i.append(split_percentage_and_points(i[2])[0])
            i.append(split_percentage_and_points(i[2])[1])
            i.pop(2)
        
        flask_session_custom["subjects"] = SubjcetList
        
        # Read subjects
        student_info = get_info(text = session.get("https://is.psjg.cz/").text)
        with open("response.html", "w", encoding="utf_8") as f:
            f.write(response.text)
        if student_info[0] == "OK":
            pass
        elif student_info[0] == "ERROR":
            raise Exception(f"Error code: {student_info[1]}")
        
        # Results ig
        flask_session_custom["studentId"] = student_info[1]
        responseGrid = session.get("https://is.psjg.cz",
                        params={
                            "studentScoreGrid-id": 1,
                            "do": "studentScoreGrid-export"
                        })
        print(responseGrid.status_code)
        with open("responsegrid.csv", "w", encoding="utf_8") as f:
            f.write(responseGrid.text)
        df = csv_to_dataframe(text=responseGrid.text)         
        
        znamky = []
        csvlist = df.values.tolist()
        
        # Add znamka to csvlist
        for x,row in enumerate(csvlist):
            znamky.append(znamka_from_percentage(row[3]))
        df["Znamka"] = znamky 
        csvlist = df.values.tolist()   
        
        #Get rid of nan values    
        for x,row in enumerate(csvlist):
            for y,item in enumerate(row):
                if pd.isna(item):               
                    csvlist[x][y] = ""
                    
        flask_session_custom["znamky"] = csvlist
            
        return redirect(url_for("home"))

    # Error handling
    except requests.exceptions.SSLError as e:
        certificates()
        print(f"\n{e}\n")
        print(traceback.format_exc())
        return render_template("error.html", exception=e, traceback=traceback.format_exc(), message="Zkuste obnovit stránku")
    
    except Exception as e:
        print(f"\n{e}\n")
        print(traceback.format_exc())
        return render_template("error.html", exception=e, traceback=traceback.format_exc(), message="")
        
#znamky
@app.route('/subject/<subject_id>')
def subject(subject_id):
    try:
        saved_cookies = flask_session_custom.get('cookies')
        student_id = flask_session_custom.get('studentId')
        
        if not saved_cookies:
            return redirect(url_for('func'))
        session = requests.Session()
        session.verify = certificate
        session.cookies.update(saved_cookies)
        
        response = session.get("https://is.psjg.cz/student/student-exam-overview",
                            params={
                                "studentExamOverview-examGrid-id": "1",
                                "studentId": student_id,
                                "subjectId": subject_id,
                                "do": "studentExamOverview-examGrid-export"
                            })
        
        #Save response to CSV  
        print(response.status_code)
        df = csv_to_dataframe(text=response.text)         
        
        znamky = []
        csvlist = df.values.tolist()
        
        # Add znamka to csvlist
        for x,row in enumerate(csvlist):
            znamky.append(znamka_from_percentage(row[5]))
        df["Znamka"] = znamky 
        csvlist = df.values.tolist()   
        
        #Get rid of nan values    
        for x,row in enumerate(csvlist):
            for y,item in enumerate(row):
                if pd.isna(item):               
                    csvlist[x][y] = ""

        #flask_session_custom["znamky"] = csvlist
    except Exception as e:
        print(f"\n{e}\n")
        print(traceback.format_exc())
        return render_template("error.html", exception=e, traceback=traceback.format_exc(), message="")
    return render_template("znamka.html", znamky = csvlist)

# -------------------------------
# REDIRECTS
# -------------------------------

@app.route('/home') 
def home():
    try:
        # Get subjects from saved cookies
        subjects = flask_session_custom.get('subjects')
        znamky = flask_session_custom.get("znamky")
        
        #Make sure it exists
        if not subjects:
            return redirect(url_for('func'))
            
    except Exception as e:
        print(f"\n{e}\n")
        print(traceback.format_exc())
        return render_template("error.html", exception=e, traceback=traceback.format_exc(), message="")
    
    # Render the template
    return render_template("home.html", subjects=subjects, znamky=znamky)

# Portfolio
@app.route('/portfolio') 
def portfolio():
    try:
        student_id = flask_session_custom.get('studentId')
        
        #Make sure it exists
        if not student_id:
            return redirect(url_for('func'))
    except Exception as e:
        print(f"\n{e}\n")
        print(traceback.format_exc())
        return render_template("error.html", exception=e, traceback=traceback.format_exc(), message="")
    
    # Render the template
    return render_template("portfolio.html")

# Zkoušení
@app.route('/zkouseni') 
def zkouseni():
    try:
        student_id = flask_session_custom.get('studentId')
        
        #Make sure it exists
        if not student_id:
            return redirect(url_for('func'))
            
    except Exception as e:
        print(f"\n{e}\n")
        print(traceback.format_exc())
        return render_template("error.html", exception=e, traceback=traceback.format_exc(), message="")
    
    # Render the template
    return render_template("zkouseni.html")
if __name__ == "__main__":
    app.run(debug=os.environ.get('DEBUG', False))