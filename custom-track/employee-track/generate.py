import json
import random
import argparse

def random_name():
    first_names = ["John", "Jane", "Alice", "Bob", "Charlie", "Eve", "Frank", "Grace", "Hank", "Ivy", "Jack", "Kathy", "Leo", "Mona", "Nina", "Oscar", "Paul", "Quinn", "Rita", "Sam"]
    last_names = ["Doe", "Smith", "Johnson", "Brown", "Davis", "Wilson", "Moore", "Lee", "Green", "Walker"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"

def random_age():
    return random.randint(20, 60)

def random_occupation():
    occupations = ["Engineer", "Designer", "Manager", "Data Scientist", "Product Manager", "Intern", "CTO", "CEO", "COO", "CFO"]
    return random.choice(occupations)

def random_location():
    locations = ["New York", "San Francisco", "Chicago", "Seattle", "Boston", "Austin", "Denver", "Atlanta", "Los Angeles", "Miami"]
    return random.choice(locations)

def random_salary():
    return random.randint(50000, 200000)

def random_sex():
    return random.choice(["M", "F"])

def random_city_of_origin():
    cities = ["Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose", "Fort Worth", "Columbus", "Charlotte",
              "Indianapolis", "San Francisco", "Seattle", "Denver", "Washington", "Boston", "El Paso", "Nashville", "Detroit", "Oklahoma City"]
    return random.choice(cities)

def random_demography():
    demographies = ["Asian", "Black", "Hispanic", "White", "Mixed", "Other"]
    return random.choice(demographies)

def generate_employee(employee_id):
    return {
        "employee_id": random.randint(1000000000, 9999999999),
        "name": random_name(),
        "age": random_age(),
        "occupation": random_occupation(),
        "location": random_location(),
        "salary": random_salary(),
        "sex": random_sex(),
        "city_of_origin": random_city_of_origin(),
        "demography": random_demography()
    }

def generate_employees(filename, num_employees):
    with open(filename, 'w') as f:
        for i in range(1, num_employees + 1):
            employee_record = generate_employee(i)
            json.dump(employee_record, f)
            f.write("\n")  # Write each JSON object on a new line without list brackets or commas

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate a JSON dataset for employees.')
    parser.add_argument('--filename', type=str, default='employee.json', help='Output file name')
    parser.add_argument('--num-employees', type=int, default=1000, help='Number of employee records to generate')
    
    args = parser.parse_args()
    generate_employees(args.filename, args.num_employees)
