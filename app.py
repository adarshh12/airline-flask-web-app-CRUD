from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import csv
import logging
import shutil
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = '4b0eae123e2f86a8493d45f8d9f3c7f42c9d2a5b9f2e96b3f1e25c6b5734a8cb'  # Set directly or use environment variables in AWS

# File paths for CSV storage
USER_CSV_FILE = 'users.csv'
TICKETS_CSV_FILE = 'tickets.csv'


# Function to read tickets from CSV
def fetch_tickets_from_csv():
    tickets = []
    try:
        with open(TICKETS_CSV_FILE, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            tickets = [row for row in reader]
    except FileNotFoundError:
        logging.warning("Tickets CSV file not found. Returning empty list.")
    return tickets


# Function to save user registration details in CSV
def save_user_to_csv(username, password):
    try:
        with open(USER_CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            file.seek(0)  # Check if file is empty
            first_char = file.read(1)
            if not first_char:
                writer.writerow(["username", "password"])  # Write header if file is empty
            writer.writerow([username, password])
    except Exception as e:
        logging.error(f"Error writing to CSV: {e}")


def fetch_users_from_csv():
    users = []
    try:
        with open(USER_CSV_FILE, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                users.append(row)
    except FileNotFoundError:
        logging.error("Users CSV file not found.")
    return users

@app.route('/')
def login():
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Save user to CSV instead of database
        try:
            save_user_to_csv(username, password)
            return redirect(url_for('login'))
        except Exception as e:
            logging.error(f"Error saving user: {e}")
            return str(e)
    return render_template('register.html')


@app.route('/home', methods=['GET', 'POST'])
def home():
    # Fetch the data from CSV (tickets)
    tickets = fetch_tickets_from_csv()

    # Get the logged-in user's username from the session
    username = session.get('username')

    # Apply filters from the form
    if request.method == 'POST':
        status_filter = request.form.get('statusFilter', 'all')
        price_filter = request.form.get('priceFilter', 'default')

        # Filter tickets based on the selected status
        if status_filter != 'all':
            tickets = [ticket for ticket in tickets if ticket['statuses'] == status_filter]

        # Sort tickets based on price filter
        if price_filter == 'high-low':
            tickets.sort(key=lambda x: float(tickets['price']), reverse=True)
        elif price_filter == 'low-high':
            tickets.sort(key=lambda x: float(tickets['price']))

    return render_template('home.html', tickets=tickets, username=username)


@app.route('/book/<ticket_id>', methods=['POST'])
def book_ticket(ticket_id):
    if 'username' not in session:
        return jsonify({'error': 'User not logged in.'}), 401

    username = session['username']
    tickets = fetch_tickets_from_csv()
    ticket_found = False

    for ticket in tickets:
        if ticket['ticket_id'] == ticket_id:
            ticket_found = True
            if ticket['statuses'] == 'booked':
                return jsonify({'error': 'Ticket already booked.'}), 400
            ticket['statuses'] = 'booked'
            ticket['users'] = username
            break

    if not ticket_found:
        return jsonify({'error': 'Ticket not found.'}), 404

    # Save updated tickets back to CSV
    try:
        with open(TICKETS_CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
            fieldnames = ['ticket_id', 'statuses', 'price', 'users']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(tickets)

        return redirect(url_for('ticket'))
    except Exception as e:
        logging.error(f"Error booking ticket: {e}")
        return str(e)


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/login', methods=['POST'])
def login_user():
    username = request.form['username']
    password = request.form['password']

    users = fetch_users_from_csv()

    # Check if the user exists and password matches
    for user in users:
        if user['username'] == username and user['password'] == password:
            session['username'] = username
            return redirect(url_for('home'))

    return "Invalid credentials, please try again."


@app.route('/add_ticket', methods=['GET', 'POST'])
def add_ticket():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in.'}), 401
    
    if request.method == 'POST':
        source = request.form['source']
        destination = request.form['destination']
        price = request.form['price']
        status = request.form['statuses']
        username = session['username']  # Get the username of the logged-in user

        # Fetch tickets to determine the next ticket_id
        tickets = fetch_tickets_from_csv()
        if tickets:
            last_ticket_id = tickets[-1]['ticket_id']  # Get last ticket_id
            ticket_number = int(last_ticket_id[1:])  # Extract numeric part
            new_ticket_id = f"T{ticket_number + 1:03d}"
        else:
            new_ticket_id = "T001"  # Start with T001 if no tickets exist

        # Append new ticket to CSV
        try:
            with open(TICKETS_CSV_FILE, mode='a+', encoding='utf-8', newline='') as file:
                fieldnames = ['ticket_id', 'source', 'destination', 'price', 'statuses', 'users']
                writer = csv.DictWriter(file, fieldnames=fieldnames)

                file.seek(0)  
                first_char = file.read(1)
                if not first_char:  
                    writer.writeheader()  # Write headers if the file is empty

                writer.writerow({
                    'ticket_id': new_ticket_id,
                    'source': source,
                    'destination': destination,
                    'price': price,
                    'statuses': status,
                    'users': username
                })

            return redirect(url_for('ticket'))  # Redirect to ticket page
        except Exception as e:
            logging.error(f"Error adding ticket: {e}")
            return str(e)

    return render_template('addticket.html')


@app.route('/ticket', methods=['GET'])
def ticket():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in.'}), 401

    username = session['username']
    tickets = fetch_tickets_from_csv()

    # Filter tickets to show only the logged-in user's bookings
    user_tickets = [ticket for ticket in tickets if ticket['users'] == username]

    return render_template('ticket.html', tickets=user_tickets)


@app.route('/update_ticket/<ticket_id>', methods=['GET', 'POST'])
def update_ticket(ticket_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    tickets = fetch_tickets_from_csv()

    # Find the ticket
    ticket = next((t for t in tickets if t['ticket_id'] == ticket_id and t['users'] == username), None)
    if not ticket:
        return jsonify({'error': 'You can only update your own tickets.'}), 403

    if request.method == 'POST':
        # Update ticket details
        ticket['destination'] = request.form['destination']
        ticket['price'] = request.form['price']
        ticket['statuses'] = request.form['statuses']

        # Rewrite the CSV file with updated ticket
        temp_file = TICKETS_CSV_FILE + ".tmp"
        try:
            with open(temp_file, mode='w', encoding='utf-8', newline='') as file:
                fieldnames = ['ticket_id', 'source', 'destination', 'price', 'statuses', 'users']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()

                for t in tickets:
                    writer.writerow(t)  # Write updated tickets

            shutil.move(temp_file, TICKETS_CSV_FILE)  # Replace old CSV
            return redirect(url_for('ticket'))  # Redirect to ticket page
        except Exception as e:
            logging.error(f"Error updating ticket: {e}")
            return str(e)

    return render_template('update_ticket.html', ticket=ticket)


@app.route('/delete_ticket/<ticket_id>', methods=['POST'])
def delete_ticket(ticket_id):
    if 'username' not in session:
        return jsonify({'error': 'User not logged in.'}), 401

    tickets = fetch_tickets_from_csv()

    # Check if ticket belongs to logged-in user
    ticket_to_delete = next((t for t in tickets if t['ticket_id'] == ticket_id and t['users'] == session['username']), None)
    if not ticket_to_delete:
        return jsonify({'error': 'Ticket not found or unauthorized deletion.'}), 403

    # Rewrite CSV without deleted ticket
    temp_file = TICKETS_CSV_FILE + ".tmp"
    try:
        with open(temp_file, mode='w', encoding='utf-8', newline='') as file:
            fieldnames = ['ticket_id', 'source', 'destination', 'price', 'statuses', 'users']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

            for t in tickets:
                if t['ticket_id'] != ticket_id:  # Skip the ticket being deleted
                    writer.writerow(t)

        shutil.move(temp_file, TICKETS_CSV_FILE)  # Replace old CSV
        return redirect(url_for('ticket'))  # Redirect to ticket page
    except Exception as e:
        logging.error(f"Error deleting ticket: {e}")
        return str(e)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    
