from flask import Flask, flash, request, redirect, url_for, render_template, jsonify
from os.path import join,dirname,realpath
from time import sleep
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
REQUEST_NAMES = ["username","password"]

@app.route('/',methods=["GET","POST"])
def func():
    if request.method == "GET":
        return render_template("index.html")
    
    # Handle POST request - get form data
    username = request.form.get("username")
    password = request.form.get("password")
    try:
        response = requests.post("https://is.psjg.cz/sign/in", verify=False, data={                                 
            "name": username,
            "password": password,
            "signIn": "Přihlásit se",
            "_do": "signInForm-submit"})
        print(response.status_code)
        #file = open(join(dirname(realpath(__file__)), "main.html"), "w", encoding="utf-8")
        #file.write(response.text)
        #file.close()
        
        if "Neplatné přihlašovací jméno nebo heslo" in response.text:
            print("True")
            return render_template("index.html", error="Neplatné přihlašovací jméno nebo heslo")        
        else:
            return response.text
    except Exception as e:
        print(f"\n{e}\n")


if __name__ == "__main__":
    app.run(debug=True)