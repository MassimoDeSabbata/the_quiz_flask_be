from flask import Flask, session, g
from flask_socketio import SocketIO
from flask_socketio import send, emit, rooms
from flask_cors import CORS, cross_origin
import re
import uuid
import base64
import json
import time

# initial app setup

app = Flask(__name__)

cors = CORS(app)

# Configuring bidirectional connection server with socketIO
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# ---- USERS LOGGING IN AND OUT ----

# Default error handler for all kind of error on socketIO
# handles all namespaces without an explicit error handler
@socketio.on_error_default
def default_error_handler(e):
    print('ERROR OCCURRED' + str(e))


# When a new user connects giving a username, a unique user id is created
# And sent back to the client. Also all connected clients are notificated of
# the new user login
@socketio.on('newUserRequest')
def handle_new_user_request(newUserData):
    newUserData['userId'] = str(uuid_url64())
    session['userId'] = newUserData['userId']
    session['counter'] = False
    emit('newUserOk', json.dumps(newUserData))
    emit('newUser', json.dumps(newUserData), broadcast=True)
    print("EMITTED USER OK")


# When a user logs in the client request for the list of the users, this request
# is broadcasted to all clients, they will respond to the first client with their data
# so that he can collect all other users data to make the users list.
@socketio.on('userListRequest')
def handle_user_list_request():
    # emitting the request to all clients
    emit('userDataRequest', broadcast=True)


# This is the response that every client send back to a new user when he logs in and
# request for the  userListRequest. The data is sent back to everyone but only the client
# that asked for it reads it.
@socketio.on('userDataRequestAck')
def handle_user_data_request_ack(userData):
    emit('userListDataResponse', json.dumps(userData), broadcast=True)


# When a user disconnects all clients are notificated so that they can remove the user
# from the user list
@socketio.on('disconnect')
def handle_disconnect():
    emit('userLeftTheRoom', json.dumps({'userId': session['userId']}), broadcast=True)


# Creates a random unique uuid
def uuid_url64():
    rv = base64.b64encode(uuid.uuid4().bytes).decode('utf-8')
    return re.sub(r'[\=\+\/]', lambda m: {'+': '-', '/': '_', '=': ''}[m.group(0)], rv)



# ---- IN-GAME FUNCTIONS ----

# When the master sends a new question, it is broadcasted to all users
@socketio.on('newQuestion')
def handle_new_question(questionData):
    emit('newQuestionToAnswer', json.dumps(questionData), broadcast=True)

# The counter, rappresenting the time left to users to answer the question, is
# managed by the server that emits its value every second, in this way all clients are
# always sincronized. The caunter can be stopped by setting FALSE to the value of the 'counter' variable
# on the session of the user (the master) that started it, this because the session is different
# for each user
@socketio.on('stopCounter')
def counter_master():
    session['counter'] = False

# The counter, rappresenting the time left to users to answer the question, is
# managed by the server that emits its value every second, in this way all clients are
# always sincronized. The counter stops if the 'counter' variable in the user session is setted FALSE
# and when the counter finishes that value must be setted FALSE anyway.
@socketio.on('startCounter')
def counter_master(data):
    session['counter'] = True
    counter = data['value'];
    while counter >= 0:
        if session['counter']:
            emit('newCounterValue', json.dumps({'value': counter}), broadcast=True)
            counter -= 1
            time.sleep(1)
        else:
            # emit('counterRemaningTime', json.dumps({'value': counter}), broadcast=True)
            break
    session['counter'] = False

# When a player want to answer a question all users are notified
@socketio.on('reserveResponse')
def handle_reserve_response(userData):
    emit('userReservedResponse', json.dumps(userData), broadcast=True)


# This function notifies all the clients when the master confirms that a user
# reserved the answer.
@socketio.on('userReservationConfirmaition')
def handle_reserve_confirmation(userData):
    emit('userReservationConfirm', json.dumps(userData), broadcast=True)


@socketio.on('userGivingAnswer')
def handle_user_giving_answer(answerData):
    emit('givenAnswer', json.dumps(answerData), broadcast=True)



# When a user reserved the answer but fails, the clients must be notified to let other players try
# so to free the reservation
@socketio.on('wrongAnswer')
def handle_wrong_answer(answerData):
    emit('freeReservations', broadcast=True)
    emit('wrongAnswerGiven', json.dumps(answerData), broadcast=True)


@socketio.on('rightAnswer')
def handle_right_answer(answerData):
    print("right answer given")
    emit('rightAnswerGiven', json.dumps(answerData), broadcast=True)



@socketio.on('reservationCounter')
def handle_reservation_counter(data):
    emit('newReservationCounterValue', json.dumps(data), broadcast=True)


if __name__ == '__main__':
    app.run()
