from flask import Flask, render_template, request, redirect, jsonify
from celery import Celery
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
app = Flask(__name__)

#Setting up Database
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///celery.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Setting up celery
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'           
# app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'db+sqlite:///celery_results.sqlite3'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# The function which will run by celery
@celery.task(bind=True) 
def long_task(self, b, c):
    a = b+c
    return {"a":a}


@app.route('/longtask', methods=['POST'])
def longtask():
    task = long_task.delay(1,2)
    return jsonify({'taskstatus' : task.id}), 202,

@app.route('/status/<task_id>')
def taskstatus(task_id):
    task = long_task.AsyncResult(task_id)
    print(task.result)
    print(task.status)
    print(task.state)
    if task.state == 'PENDING':
        # job did not start yet
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True)