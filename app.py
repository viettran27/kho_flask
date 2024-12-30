import os
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import urllib.parse
from dotenv import load_dotenv

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
  
    if duplicates:
      return {
        "type": "error",
        "message": f"Bị trùng barcode: {', '.join(map(str, duplicates))}"
      }

    return {
      "type": "success",
      "message": "Thêm thành công"
    }
  
  except Exception as e:
    print(e)
    return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=93, debug=True)
