from bs4 import BeautifulSoup, diagnose
import csv

def delete_spaces(text):
    return text.replace("\n", "").replace("\t", "").replace(" ", "")

with open ("main.html", "r", encoding="utf-8") as file:
    with open('names.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Předmět', 'Bodové hodnocení',"Známka","Výsledná známka"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames,delimiter=';')

        writer.writeheader()
        soup = BeautifulSoup(file, "html.parser")
        try:  
            for table in soup.find_all('table'):
                if table.tr.th.text == "Předmět":
                    for tr in table.find_all('tr'):
                        sezam = []
                        for i,td in enumerate(tr.find_all('td')):
                            sezam.append(delete_spaces(td.text))
                            if i == 3:
                                writer.writerow({'Předmět': f'{sezam[0]}', 'Bodové hodnocení': f'{sezam[1]}', "Známka": f'{sezam[2]}', "Výsledná známka": f'{sezam[3]}'})

        except Exception as e:
            print(f"\n{e}\n")
            diagnose(soup)
        finally:
            file.close()
            csvfile.close()
        