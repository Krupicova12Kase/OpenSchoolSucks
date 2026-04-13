###############################
# Made by Krupicova12Kase AKA Máťa
# Licensed under MIT license
# Report any bugs at https://github.com/Krupicova12Kase/OpenSchoolSucks/issues
###############################

#Imports
import traceback
from flask import Flask, flash, request, redirect, url_for, render_template, jsonify, session as flask_session
import os
import requests
from bs4 import BeautifulSoup, diagnose
import csv
from io import *
import re
import pandas as pd
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
REQUEST_NAMES = ["username","password"]

#Requests session
certificate = os.path.join(os.path.dirname(__file__), 'psjg_chain.crt')

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
    subject_mappings = {}
    # Get full HTML webpage (Kdo tohle sakra dělal, kdyby to bylo na mě, tak udělám API)
    soup = BeautifulSoup(text, "html.parser")
    for table in soup.find_all('table'): #Find all tables in the HTML file
        if table.tr.th.text == "Předmět": #Search only for table with list of subjects
            for tr in table.find_all('tr'): #Iterate through rows
                for a_tag in tr.find_all('a'): #Search through links
                    url = a_tag.get("href") #Get URL from link
                    query = urlparse(url).query
                    params = parse_qs(query)

                    subject_id = params.get('subjectId')[0]
                    student_id = params.get('studentId')[0]
                    
                    subject_mappings.update({subject_id: a_tag.get_text()})
                    sezam.append([student_id, subject_id])
            break
    
    # Process subject Ids
    subjectIds = []
    for i in sezam:
        subjectIds.append(i[1]) 
         
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
    
    return ("OK", student_id, subjectIds, subject_mappings)

# Gets subjects from HTML text
def get_csv_subjects(text:str, fieldnames:list) -> tuple:
    csvfile = StringIO()
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames,delimiter=';')

    writer.writeheader()
    soup = BeautifulSoup(text, "html.parser")
    try:  
        for table in soup.find_all('table'): #Find all tables in the HTML file
            if table.tr.th.text == "Předmět": #Search only for table with list of subjects
                for tr in table.find_all('tr'): #Iterate through rows
                    sezam = []
                    for i,td in enumerate(tr.find_all('td')): #Iterate through columns
                        sezam.append(delete_spaces(td.text))
                        if i == 3:
                            writer.writerow({'Předmět': f'{sezam[0]}', 'Bodové hodnocení': f'{sezam[1]}', "Známka": f'{sezam[2]}', "Výsledná známka": f'{sezam[3]}'})
                            #print(f"{sezam[0]} {sezam[1]} {sezam[2]} {sezam[3]}")
        return ("OK",csvfile)
    except Exception as e:
        return ("ERROR",diagnose(soup),e)                

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
                
@app.route('/',methods=["GET","POST"])
def func():
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
    try:
        response = session.post("https://is.psjg.cz/sign/in", data={                                 
            "name": username,
            "password": password,
            "signIn": "Přihlásit se",
            "_do": "signInForm-submit"})
        print(response.status_code)
        
        flask_session["cookies"] = session.cookies.get_dict()
        
        if "Neplatné přihlašovací jméno nebo heslo" in response.text:
            return render_template("index.html", error="Neplatné přihlašovací jméno nebo heslo") 
    
        # Get subjects from HTML response and write them to CSV file
        fieldnames = ['Předmět', 'Bodové hodnocení',"Známka","Výsledná známka"] #List of column names for CSV file
        subjects = get_csv_subjects(response.text, fieldnames)
        if subjects[0] == "OK":
            csvfile = subjects[1]
        elif subjects[0] == "ERROR":
            print(f"{subjects[1]},\n{subjects[2]}")
        
        # Read subjects
        subjects = []
        csvfile.seek(0)
        reader = csv.reader(csvfile, delimiter=';')
        next(reader) #Skip header row
        for row in reader:
            subjects.append(row)
        
        student_info = get_info(text = session.get("https://is.psjg.cz/").text)
        if student_info[0] == "OK":
            pass
        elif student_info[0] == "ERROR":
            return "Error"
        
        # -------------------------------
        # HOMEPAGE
        # -------------------------------

        # Results ig
        flask_session["studentId"] = student_info[1]
        response2 = session.get("https://is.psjg.cz/student/student-exam-overview",
                        params={
                            "studentExamOverview-examGrid-id": "1",
                            "studentId": student_info[1],
                            "subjectId": "1619",
                            "do": "studentExamOverview-examGrid-export"
                        })
        print(response2.status_code)

        flask_session["subjects"] = student_info[3]
        return redirect(url_for("home"))
        # Error handling
    except Exception as e:
        print(f"\n{e}\n")
        print(traceback.format_exc())
        return f"""
        <h1>Máťa něco pokazil...</h1>
        <br>
        <h3>Chyba:</h3><br>
        <code>{e}</code>
        <h3>Detaily (stack trace):</h3><br>
        <code>{traceback.format_exc()}</code>"""
        
#znamky
@app.route('/subject/<subject_id>')
def subject(subject_id):
    saved_cookies = flask_session.get('cookies')
    student_id = flask_session.get('studentId')
    
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
    
    print(csvlist)

    flask_session["znamky"] = csvlist
    return render_template("znamka.html", znamky = csvlist)
    #return redirect(url_for("znamka"))   

# -------------------------------
# REDIRECTS
# -------------------------------
 
@app.route('/home') 
def home():
    # Get subjects from saved cookies
    subjects = flask_session.get('subjects')
    
    #Make sure it exists
    if not subjects:
        return redirect(url_for('func'))
        
    # Render the template
    return render_template("home.html", subjects=subjects)

if __name__ == "__main__":
    app.run(debug=False)