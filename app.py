import os
from flask import Flask, render_template, jsonify, request, send_file
from flask_sqlalchemy import SQLAlchemy
import urllib.parse
from dotenv import load_dotenv
import pandas as pd
import io

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

database_server = os.environ.get("HOST")
database_name = os.environ.get("DATABASE")
database_user = os.environ.get("USERNAME_DB")
database_password = os.environ.get("PASSWORD_DB")

params = urllib.parse.quote_plus(
  "DRIVER={ODBC Driver 17 for SQL Server};"
  f"SERVER={database_server};"
  f"DATABASE={database_name};"
  f"UID={database_user};"
  f"PWD={database_password};"
)

app.config["SQLALCHEMY_DATABASE_URI"] = f"mssql+pyodbc:///?odbc_connect={params}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
@app.route('/')
def home():
    return render_template('index.html')

class Inventory(db.Model):
  __tablename__ = 'KIEM_KE'
  Carton_Barcode = db.Column(db.String, primary_key=True)
  Time_Stamp = db.Column(db.String)

class Summary(db.Model):
  __tablename__ = 'BAO_CAO_KIEM_KE'
  Carton_Barcode = db.Column(db.String, primary_key=True)
  QR_Code = db.Column(db.String)
  SO_NO = db.Column(db.String)
  PO_NO = db.Column(db.String)
  MO_NO = db.Column(db.String)
  PackingWay_Code = db.Column(db.String)
  Carton_No = db.Column(db.Integer)

@app.route('/insert_inventory', methods=['POST'])
def insert_inventory():
  try:
    inventory_data = request.json
    inventory_codes = {item['code'] for item in inventory_data}

    existing_inventories = Inventory.query.filter(Inventory.Carton_Barcode.in_(inventory_codes)).all()
    existing_codes = {inventory.Carton_Barcode for inventory in existing_inventories}

    duplicates = inventory_codes.intersection(existing_codes)
    new_inventories = [Inventory(Carton_Barcode=item['code'], Time_Stamp=item['datetime']) for item in inventory_data if item['code'] not in existing_codes]

    if new_inventories:
      db.session.add_all(new_inventories)
      db.session.commit()
    
    count = Inventory.query.count()
  
    if duplicates:
      return {
        "type": "error",
        "count": count,
        "message": f"Bị trùng barcode: {', '.join(map(str, duplicates))}"
      }

    return {
      "type": "success",
      "count": count,
      "message": "Thêm thành công"
    }
  
  except Exception as e:
    print(e)
    return jsonify({'error': str(e)}), 500

@app.route('/download_excel')
def download_excel():
  summaries = Summary.query.all()
  summaries_data = [{
    "Carton_Barcode": summary.Carton_Barcode,
    "QR_Code": summary.QR_Code,
    "SO_NO": summary.SO_NO,
    "PO_NO": summary.PO_NO,
    "MO_NO": summary.MO_NO,
    "PackingWay_Code": summary.PackingWay_Code,
    "Carton_No": summary.Carton_No
  } for summary in summaries]

  df = pd.DataFrame(summaries_data)
  output = io.BytesIO()
  writer = pd.ExcelWriter(output)
  df.to_excel(writer, index=False, sheet_name='Summaries')
  writer._save()
  output.seek(0)

  return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', download_name=f'kiemke.xlsx', as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=93, debug=True)
