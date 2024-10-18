import argparse
import requests
import string
import random

URL = "127.0.0.1"


def register_new_users(num_users):
    print(f"Creating {num_users} new users")
    for i in range(num_users):
        username_len = random.randint(5, 20)
        username = 'user_' + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(username_len))
        password_len = random.randint(8, 20)
        password = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(password_len))
        with open("created_users.txt", "a") as f:
            f.write(username + " " + password + "\n")
        req = requests.post(f"http://{URL}:5000/register", data={"username": username, "password": password, "repassword": password})
        print(req.status_code, "for creating user:", username, "password:", password)


def create_food_records(num_records, username):
    print(f"Creating {num_records} food records for user: {username}")


def create_weight_records(num_records, username):
    print(f"Creating {num_records} weight records for user: {username}")


def main(args):
    if args.create_users:
        register_new_users(args.create_users)
    
    if args.create_foods and not args.username:
        print("When generating food records you need to specify username for whom those shall be created for with '--username X'")
    elif args.create_foods and args.username:
        create_food_records(args.create_foods, args.username)

    if args.create_weights and not args.username:
        print("When generating weight records you need to specify username for whom those shall be created for with '--username X'")
    elif args.create_weights and args.username:
        create_weight_records(args.create_weights, args.username)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--create_users", type=int, default=0)
    parser.add_argument("--create_foods", type=int, default=0)
    parser.add_argument("--create_weights", type=int, default=0)
    parser.add_argument("--username", type=str)
    args = parser.parse_args()

    main(args)