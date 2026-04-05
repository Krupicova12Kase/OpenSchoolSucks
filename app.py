#Imports
from urllib import response

from flask import Flask, flash, request, redirect, url_for, render_template, jsonify
from os.path import join,dirname,realpath
from time import sleep
import requests
from bs4 import BeautifulSoup, diagnose
import csv
from io import StringIO
import certifi
import urllib3
import re

app = Flask(__name__)
REQUEST_NAMES = ["username","password"]

#Requests session
session = requests.Session()
session.verify = certifi.where()

# Delte unnecessary spaces, tabs and newlines from text
def delete_spaces(text:str) -> str:
    return re.sub(r'\s+', ' ', text.strip())

def get_csv_subjects(text:str, fieldnames:list):
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
                
@app.route('/',methods=["GET","POST"])
def func():
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
            "_do": "signInForm-submit"},
            verify=certifi.where())
        print(response.status_code)
        
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
        response2 = session.get("https://is.psjg.cz/student/student-exam-overview",
                        params={
                            "studentExamOverview-examGrid-id": "1",
                            "studentId": "3881",
                            "subjectId": "1619",
                            "do": "studentExamOverview-examGrid-export"
                        },
                        verify=certifi.where())
        print(response2.status_code)
        print(response2.text)
        print(response2)
                     
        if "Neplatné přihlašovací jméno nebo heslo" in response.text:
            return render_template("index.html", error="Neplatné přihlašovací jméno nebo heslo")        
        else:
            file = open("test.html","w",encoding="utf-8")
            file.write(response2.text)
            file.close()
            return response2.text
    except Exception as e:
        print(f"\n{e}\n")
        return f"<h1>Máťa něco pokazil...</h1><br><h3>Chyba:</h3><br>{e}"

if __name__ == "__main__":
    app.run(debug=True)