from flask import render_template, request, redirect, url_for,json
from app import app
import os
import redis
import uuid
import base64
from flask_socketio import SocketIO,send, emit
from faker import Faker

r = redis.Redis(host='localhost', port=6379, db=0)
app.config['UPLOAD_FOLDER'] = 'app/static/uploads'
socketio = SocketIO(app)
fake = Faker()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi', 'mkv'}

def is_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg', 'png', 'gif'}

def is_video(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'mp4', 'mov', 'avi', 'mkv'}

from flask import render_template

@app.route('/')
def index():
    posts = []
    keys = r.keys('*')
    for key in keys:
        post_data = r.hgetall(key)
        if not key.startswith(b'animal:'):  # Excluimos las publicaciones de animales en peligro de extinción
            post = {
                'id': key.decode(),
                'topic': post_data.get(b'topic', b'').decode('utf-8'),
                'text': post_data.get(b'text', b'').decode('utf-8'),
                'image': base64.b64encode(post_data.get(b'image', b'')).decode('utf-8'),
                'video': post_data.get(b'video', b'').decode('utf-8'),
                'comments': []
            }
            for field, value in post_data.items():
                if field.startswith(b'comment:'):
                    comment_id = field.decode().split(':')[1]
                    comment_text = value.decode('utf-8')
                    post['comments'].append({'id': comment_id, 'text': comment_text})
            posts.append(post)
    return render_template('index.html', posts=posts)

@app.route('/chat')
def chat():
    # Obtener los mensajes guardados en Redis como un hash
    messages = r.hgetall('messages')
    message_list = []

    # Procesar los mensajes para enviarlos a través de SocketIO
    for message_id, message_data in messages.items():
        message = {
            'id': message_id.decode(),
            'data': json.loads(message_data.decode())
        }
        message_list.append(message)

    # Emitir los mensajes a través de SocketIO para mostrarlos en todas las pestañas
    emit('message_list', message_list, broadcast=True, namespace='/chat')

    return render_template('chat.html')


@socketio.on('message')
def handle_message(data):
    if 'username' not in data:
        return
    username = data['username']
    message = data['message']
    message_id = str(uuid.uuid4())

    # Guardar el mensaje como un hash en Redis
    r.hset('messages', message_id, json.dumps({'username': username, 'message': message}))

    # Emitir el mensaje a través de SocketIO
    emit('message', {'username': username, 'message': message}, broadcast=True)

def emit_saved_messages():
    # Obtener los mensajes guardados en Redis como un hash
    messages = r.hgetall('messages')
    message_list = []

    # Procesar los mensajes para enviarlos a través de SocketIO
    for message_id, message_data in messages.items():
        message = json.loads(message_data)
        message_list.append({'id': message_id.decode(), 'data': message})

    # Emitir los mensajes a través de SocketIO para mostrarlos en todas las pestañas
    emit('message_list', message_list, broadcast=True, namespace='/chat')

def emit_message(message_id):
    # Obtener el mensaje recién guardado en Redis
    message_data = json.loads(r.hget('messages', message_id))

    # Emitir el mensaje a través de SocketIO para mostrarlo en todas las pestañas
    emit('message', {'id': message_id, 'data': message_data}, broadcast=True, namespace='/chat')


@app.route('/posts')
def posts():
    posts = []
    keys = r.keys('*')
    for key in keys:
        # Aquí puedes definir la lógica para cargar solo los datos de publicaciones que no sean animales en peligro de extinción
        # Por ejemplo, podrías filtrar las claves que no tienen el prefijo 'animal:'
        if not key.startswith(b'animal:'):
            post_data = r.hgetall(key)
            post = {
                'id': key.decode(),
                'topic': post_data.get(b'topic', b'').decode('utf-8'),
                'text': post_data.get(b'text', b'').decode('utf-8'),
                'image': base64.b64encode(post_data.get(b'image', b'')).decode('utf-8'),
                'video': post_data.get(b'video', b'').decode('utf-8'),
                'comments': []
            }
            for field, value in post_data.items():
                if field.startswith(b'comment:'):
                    comment_id = field.decode().split(':')[1]
                    comment_text = value.decode('utf-8')
                    post['comments'].append({'id': comment_id, 'text': comment_text})
            posts.append(post)
    return render_template('index.html', posts=posts)

@app.route('/animal_upload', methods=['GET', 'POST'])
def animal_upload():
    if request.method == 'POST':
        name = request.form.get('name', '')
        description = request.form.get('description', '')
        
        # Procesar la imagen cargada
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[-1]
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_data = open(file_path, 'rb').read()
            else:
                # Handle invalid file format
                return "Formato de archivo no compatible"
        else:
            # Handle no file uploaded
            return "No se ha proporcionado ninguna imagen"

        # Generar una nueva clave para el animal en Redis
        animal_key = f"animal:{uuid.uuid4()}"
        
        # Guardar los datos del animal en Redis, incluida la imagen
        animal_data = {'name': name, 'description': description, 'image': image_data}
        r.hmset(animal_key, animal_data)

        # Redirigir a la misma página para mostrar la lista actualizada de animales
        return redirect(url_for('endangered_animals'))

    # Renderizar el formulario para cargar animales si es una solicitud GET
    return render_template('animal_upload.html')
@app.route('/endangered_animals', methods=['GET', 'POST'])
def endangered_animals():
    if request.method == 'POST':
        name = request.form.get('name', '')
        description = request.form.get('description', '')
        category = request.form.get('category', '')  # Obtener la categoría del formulario
        counter = request.form.get('counter', 0)  # Obtener el contador del formulario, con valor predeterminado 0 si no se proporciona
        
        # Procesar la imagen cargada
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[-1]
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_data = open(file_path, 'rb').read()
            else:
                # Handle invalid file format
                return "Formato de archivo no compatible"

        animal_key = f"animal:{uuid.uuid4()}"
        # Agregar categoría y contador al diccionario animal_data
        animal_data = {'name': name, 'description': description, 'image': image_data, 'category': category, 'counter': counter}
        r.hmset(animal_key, animal_data)

        # Redirigir a la misma página para mostrar la lista actualizada de animales
        return redirect(url_for('endangered_animals'))

    else:
        animals = []
        animal_keys = r.keys('animal:*')
        for key in animal_keys:
            animal_data = r.hgetall(key)
            animal = {
                'name': animal_data.get(b'name', b'').decode('utf-8'),
                'description': animal_data.get(b'description', b'').decode('utf-8'),
                'category': animal_data.get(b'category', b'').decode('utf-8'),  # Obtener la categoría del diccionario
                'counter': animal_data.get(b'counter', 0).decode('utf-8'),  # Obtener el contador del diccionario y asignar 0 si no está presente
                'image': base64.b64encode(animal_data.get(b'image', b'')).decode('utf-8'),
            }
            animals.append(animal)
        return render_template('endangered_animals.html', animals=animals)


@app.route('/upload', methods=['POST'])
def upload():
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                topic = request.form.get('topic', '')
                text = request.form.get('text', '')
                filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[-1]
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Check if the uploaded file is an image or video
                if is_image(file.filename):
                    with open(file_path, 'rb') as f:
                        file_data = f.read()
                    r.hmset(filename, {'topic': topic, 'text': text, 'image': file_data})
                elif is_video(file.filename):
                    r.hmset(filename, {'topic': topic, 'text': text, 'video': filename})
                else:
                    return "Formato de archivo no compatible"
                
                return redirect(url_for('index'))
            else:
                return "Formato de archivo no compatible"
        else:
            # Handle the case where no file is uploaded
            return "No se ha proporcionado ningún archivo"

@app.route('/comment', methods=['POST'])
def comment():
    if request.method == 'POST':
        post_id = request.form['post_id']
        comment_text = request.form['comment']
        post_key = f"{post_id}"
        comment_id = str(uuid.uuid4())
        r.hset(post_key, f"comment:{comment_id}", comment_text)
        return redirect(url_for('index'))
