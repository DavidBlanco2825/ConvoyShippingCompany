""" Convoy Shipping Company """
import csv
import json
import math
import re
import sqlite3
import pandas as pd


def xlsx_to_csv(xlsx_name, csv_name):
    """ Convert a xlsx file to a csv file"""
    xlsx_df = pd.read_excel(f"{xlsx_name}", sheet_name='Vehicles', dtype=str)
    n = xlsx_df.shape[0]
    xlsx_df.to_csv(f"{csv_name}", index=False)
    print(f'{n} {"lines were" if n > 1 else "line was"} added to {csv_name}')
    checked_name = xlsx_name.replace(".xlsx", "[CHECKED].csv")
    fix_data(csv_name, checked_name)


def fix_data(csv_name, checked_name):
    """ Remove non-integer values from cells, if a cell contains only non-integer values it is replaced with zero."""
    raw_data = [line for line in csv.reader(open(csv_name))]
    data = raw_data.copy()
    fix = 0
    for i in range(1, len(data)):
        for j in range(0, len(data[i])):
            num = len(data[i][j])
            # data[i][j] = re.sub("[\D]", "", data[i][j])
            data[i][j] = re.sub('[a-z._]', '', data[i][j]).strip()
            if num != len(data[i][j]):
                fix += 1
    with open(f"{checked_name}", "w", encoding="utf-8") as f_file:
        file_writer = csv.writer(f_file, delimiter=",", lineterminator="\n")
        for i in data:
            file_writer.writerow(i)
    print(f'{fix} {"cells were" if fix > 1 else "cell was"} corrected in {checked_name}')
    create_db(checked_name)


def score_evaluation(tank_capacity, fuel_consumption, payload):
    """ A method for calculating the vehicle score """
    route_length = 450  # km
    consumed_fuel = (route_length / 100) * fuel_consumption  # km * liters/100 kilometers
    pit_stops = math.floor(consumed_fuel / tank_capacity)
    vehicle_score = 0
    vehicle_score += 2 if pit_stops == 0 else (1 if pit_stops == 1 else 0)
    vehicle_score += 2 if consumed_fuel <= 230 else 1
    vehicle_score += 2 if payload >= 20 else 0
    return vehicle_score


def create_db(checked_name):
    """ Generate a SQLite3 DB from a [CHECKED] csv file """
    db_name = checked_name.replace("[CHECKED].csv", ".s3db")
    con = sqlite3.connect(f"{db_name}")
    cursor = con.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS convoy(
                        vehicle_id INT PRIMARY KEY NOT NULL,
                        engine_capacity INT NOT NULL,
                        fuel_consumption INT NOT NULL,
                        maximum_load INT NOT NULL,
                        score INT NOT NULL);''')
    con.commit()
    vehicle_data = [line for line in csv.reader(open(checked_name))]

    for i in range(len(vehicle_data)):
        if i == 0:
            vehicle_data[i].append("score")
        else:
            vehicle = vehicle_data[i]
            vehicle_score = score_evaluation(int(vehicle[1]), float(vehicle[2]), int(vehicle[3]))
            vehicle.append(str(vehicle_score))

    rows = 0
    for j in range(1, len(vehicle_data)):
        row = tuple(vehicle_data[j])
        cursor.execute(
            "INSERT OR REPLACE INTO convoy(vehicle_id, engine_capacity, fuel_consumption, maximum_load, score) VALUES ("
            "?, ?, ?, ?, ?)", row)
        rows += 1
        con.commit()
    print(f'{rows} {"records were" if rows > 1 else "record was"} inserted into {db_name}')
    con.commit()
    create_json(db_name)
    create_xml(db_name)
    con.close()


def create_json(db_name):
    """ Save selected entities from a SQLite3 DB to a json file """
    con = sqlite3.connect(db_name)
    json_data = pd.read_sql_query("SELECT vehicle_id, engine_capacity, fuel_consumption, maximum_load"
                                  " FROM convoy"
                                  " WHERE score > 3", con)
    json_name = db_name.replace(".s3db", ".json")
    convoy_dict = json_data.to_dict(orient="records")
    with open(json_name, "w") as json_file:
        json.dump({"convoy": convoy_dict}, json_file)
        print(f'{len(convoy_dict)} {"vehicles were" if len(convoy_dict) > 1 else "vehicle was"} saved into {json_name}')
    con.close()


def create_xml(db_name):
    """ Save selected entities from a SQLite3 DB to a json file """
    con = sqlite3.connect(db_name)
    xml_data = pd.read_sql_query("SELECT vehicle_id, engine_capacity, fuel_consumption, maximum_load"
                                 " FROM convoy"
                                 " WHERE score <= 3", con)
    xml_name = db_name.replace(".s3db", ".xml")
    xml = xml_data.to_xml(root_name='convoy', row_name='vehicle', xml_declaration=False, index=False)
    with open(xml_name, 'w') as xml_file:
        xml_file.write("<convoy></convoy>" if len(xml_data) == 0 else xml)
    print(f'{len(xml_data)} {"vehicle was" if len(xml_data) == 1 else "vehicles were"} saved into {xml_name}')
    con.close()


def main():
    file_name = input("Input file name \n")

    # Handle .xlsx dirty file
    if file_name.endswith(".xlsx"):
        xlsx_name = file_name
        csv_name = file_name.replace(".xlsx", ".csv")
        xlsx_to_csv(xlsx_name, csv_name)

    # Handle .csv clean file
    elif file_name.endswith("[CHECKED].csv"):
        checked_name = file_name
        create_db(checked_name)

    # Handle .csv dirty file
    elif file_name.endswith(".csv"):
        csv_name = file_name
        checked_name = file_name.replace(".csv", "[CHECKED].csv")
        fix_data(csv_name, checked_name)

    # Handle .s3bd file
    elif file_name.endswith(".s3db"):
        create_json(file_name)
        create_xml(file_name)
        # data_gather(file_name)


if __name__ == '__main__':
    main()
