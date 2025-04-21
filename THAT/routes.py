from flask import render_template, url_for, flash, redirect,request,abort,jsonify,session
import requests
import json
import imaplib
from THAT import application,db,bcrypt,mail #using bcrypt to has the passwords in user database
from THAT.models import User, Lecture
from THAT.forms import RegistrationForm, LoginForm,LectureForm,SearchForm,MessageForm,UpdateAccountForm,FeedbackForm

from flask_login import login_user,current_user,logout_user,login_required
from sqlalchemy.orm.exc import NoResultFound

from datetime import datetime, timedelta
from random import sample
from THAT.search import KMPSearch

import urllib.request
import urllib.parse
from flask_mail import Message

#--------------------------------------------------------------------------------------------
import time
import string
import pyaudio
import speech_recognition as sr
from plyer import notification 
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER
from nltk.tokenize import sent_tokenize, word_tokenize 
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from THAT.features import getRoS, getTranscript, makesrt
#--------------------------------------------------------------------------------------------

import os
from os import path
import moviepy.editor as mp
from werkzeug.utils import secure_filename

# Add this near your other imports
from THAT import application
import openai

# Add these configs after the imports
UPLOAD_FOLDER = 'THAT/static/video'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv'}

# Add this config to the application
application.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Add this after your imports
from dotenv import load_dotenv
load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')# Add this function before the routes
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#--------------------------------------------------------------------------------------------
#everything here that begins with @ is a decorator
@application.route("/")
@application.route("/home", methods=['GET', 'POST'])

@application.route("/home")
def home():
    return render_template('home.html',db=db,User=User,Lecture=Lecture)

@application.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))  
    form = LoginForm()
    if form.validate_on_submit():
        user=User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password,form.password.data):
            login_user(user, remember=form.remember.data)
            next_page=request.args.get('next')#looks for queries in request; args is a dictionary; we use get and not directly use 'next' as key to return the value because key might be empty leading to an error. get, in that case would fetch a none
            flash('Greetings '+form.username.data+'!','success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@application.route("/dashboard", methods=['GET', 'POST'])
@login_required
def dashboard():
    if current_user.user_type == 'Professor':
        lectures=Lecture.query.filter_by(user_id=current_user.id).all()
    else:
        lectures=Lecture.query.all()
        
    lectures.reverse()
    form1=SearchForm()
    if form1.validate_on_submit():
        arr=[] 
        lectures2=[]
        for lecture in lectures:
            a=form1.search.data
            b=lecture.title
            if KMPSearch(a.casefold(),b.casefold()):
                arr.append(lecture.id)
                lectures2.append(Lecture.query.filter_by(id=lecture.id).first())
        if len(arr)==0:
            flash('Lecture not found!','warning')
            return redirect(url_for('dashboard'))
        else:
            data=json.dumps(form1.search.data)
            return render_template('search_lecture.html', title='Searched Lecture', lectures2=lectures2,data=data)
    return render_template('dashboard.html', title='Dashboard', lectures=lectures,form1=form1)
    

@application.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard')) #redirects user to dashboard if already logged in; function name is passed in url_for
    form = RegistrationForm()
    if form.validate_on_submit():

        hashed_password=bcrypt.generate_password_hash(form.password.data).decode('utf-8') #returns hashed password, decode converts it from byte to string
        #if app_password field is not-empty
        user=User(username=form.username.data,email=form.email.data,user_type = form.user_type.data,password=hashed_password)

        db.session.add(user)
        db.session.commit()
        flash(f'You have successfully registered.', 'success')
        return redirect(url_for('dashboard'))
    image_file=url_for('static',filename='images/user.png')
    return render_template('register.html', title='Register', image_file=image_file,form=form)

@application.route("/logout")
def logout():
    logout_user()
    flash('You have logged out  !','success')
    return redirect(url_for('home'))

@application.route("/account")
@login_required
def account():
    image_file=url_for('static',filename='images/user.png')
    return render_template('account.html',title='Account',image_file=image_file)

@application.route("/account/update",methods=['GET', 'POST'])
@login_required
def update_account():
    form=UpdateAccountForm()
    if form.validate_on_submit():
       # hashed_password=bcrypt.generate_password_hash(form.password.data).decode('utf-8') #returns hashed password, decode converts it from byte to string
        current_user.username=form.username.data
        current_user.email=form.email.data
        db.session.commit()
        flash('Account updated successfully!','success')
        return redirect(url_for('account'))
    elif request.method=='GET':  #if submit btn is not clicked and account page is requested, it eill already fill the usename field with existing data
        form.username.data=current_user.username
        form.email.data=current_user.email
    image_file=url_for('static',filename='profile_pics/' + current_user.image_file)
    return render_template('update_account.html',title='Update Account',image_file=image_file,form=form,legend='Update credentials')

@application.route("/account/delete",methods=['GET', 'POST'])
@login_required
def delete_account():
    user=User.query.filter_by(id=current_user.id).first()
    lectures=Lecture.query.filter_by(user_id=current_user.id).all()
    for lecture in lectures:
        db.session.delete(lecture)
    db.session.commit()
    db.session.delete(user)
    db.session.commit()
    flash('Account deleted','success')
    return redirect(url_for('home'))

@application.route("/lecture/new", methods=['GET', 'POST'])
@login_required
def new_lecture():
    form = LectureForm()
    if form.validate_on_submit():
        video_file = request.files.get('video')
        if video_file and allowed_file(video_file.filename):
            try:
                # Secure the filename
                filename = secure_filename(video_file.filename)
                # Generate unique filename using timestamp
                unique_filename = f"{int(time.time())}_{filename}"
                # Save the file
                video_path = os.path.join('video', unique_filename)
                full_path = os.path.join(application.config['UPLOAD_FOLDER'], unique_filename)
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Save the file
                video_file.save(full_path)
                
                # Generate SRT file
                base_name = os.path.splitext(unique_filename)[0]
                srt_filename = f"{base_name}.srt"
                vtt_filename = f"{base_name}.vtt"
                srt_path = os.path.join('video', srt_filename)
                full_srt_path = os.path.join(application.config['UPLOAD_FOLDER'], srt_filename)
                
                # Create SRT file using makesrt function
                print(f"Generating SRT file for {unique_filename}...")
                result = makesrt(full_path, full_srt_path)
                
                # Check if SRT creation was successful
                if isinstance(result, str) and result.startswith("Error"):
                    subtitle_path = None
                    flash(f'Video uploaded but subtitle generation failed: {result}', 'warning')
                else:
                    subtitle_path = srt_path
                    
                    # Check if files were actually created
                    if os.path.exists(full_srt_path):
                        print(f"SRT file created successfully at {full_srt_path}")
                        with open(full_srt_path, 'r', encoding='utf-8') as f:
                            print(f"First 5 lines of SRT file:\n{''.join(f.readlines()[:5])}")
                    else:
                        print(f"WARNING: SRT file does not exist at {full_srt_path}")
                    
                    # Check for VTT file too
                    full_vtt_path = os.path.join(application.config['UPLOAD_FOLDER'], vtt_filename)
                    if os.path.exists(full_vtt_path):
                        print(f"VTT file created successfully at {full_vtt_path}")
                    
                    flash('Video and subtitles successfully created!', 'success')
                
                # Create lecture with video path and subtitle path
                lecture1 = Lecture(
                    title=form.title.data,
                    date=form.date.data,
                    starttime=form.starttime.data,
                    endtime=form.endtime.data,
                    details=form.details.data,
                    video_path=video_path,
                    subtitle_path=subtitle_path,
                    user_id=current_user.id
                )
                db.session.add(lecture1)
                db.session.commit()
                flash('Lecture scheduled and video uploaded successfully!', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e:
                flash(f'Error processing video: {str(e)}', 'danger')
                return redirect(url_for('new_lecture'))
        else:
            flash('Invalid video file. Allowed formats are: mp4, avi, mov, wmv', 'danger')
    return render_template('upload_lecture.html', title='New Lecture', form=form, legend='Schedule Lecture')


@application.route("/lecture/ <int:lecture_id>")
@login_required
def lecture(lecture_id):
    lecture=Lecture.query.get_or_404(lecture_id) #get_or_404 returns the requested page if it exists else it returns a 404 error
    return render_template('lecture.html',title=lecture.title,lecture=lecture)

@application.route("/lecture/ <int:lecture_id>/update",methods=['GET', 'POST'])
@login_required
def update_lecture(lecture_id):
    lecture=Lecture.query.get_or_404(lecture_id)
    if lecture.user_id!=current_user.id:  # this is optional since we display only a prticular user's lectures in his dashboard
        abort(403)
    form=LectureForm()
    if form.validate_on_submit():
        lecture.title = form.title.data
        lecture.details = form.details.data
        lecture.date=form.date.data
        lecture.starttime=form.starttime.data
        lecture.endtime=form.endtime.data
        db.session.commit()
        flash('Lecture updated!', 'success')
        return redirect(url_for('lecture',lecture_id=lecture.id))
    elif request.method == 'GET':
        form.title.data = lecture.title
        form.details.data = lecture.details
        form.date.data=lecture.date
        form.starttime=form.starttime
        form.endtime=form.endtime
    return render_template('upload_lecture.html', title='Update Lecture',form=form, legend='Update Lecture')

@application.route("/lecture/ <int:lecture_id>/delete",methods=['GET', 'POST'])

@login_required
def delete_lecture(lecture_id):
    lecture=Lecture.query.get_or_404(lecture_id)
    if lecture.user_id!=current_user.id:  # this is optional since we display only a prticular user's lectures in his dashboard
        abort(403)
    db.session.delete(lecture)
    db.session.commit()
    flash('Lecture deleted!','warning')
    return redirect(url_for('dashboard'))

@application.route("/contact_us",methods=['GET', 'POST'])
def contact_us():
    form=MessageForm()
    if current_user.is_authenticated:
        form.email.data=current_user.email
    if form.validate_on_submit():
        msg=Message('Sent by THAT user: '+current_user.username,sender=form.email.data,recipients=['that.admn@gmail.com']) 
        msg.body=f'''Sent from THAT contact us page:
        {form.message.data}'''
        mail.send(msg)
        flash('Your message has been sent.','success')
    return render_template("contact_us.html",form=form)

@application.route("/feedback",methods=['GET', 'POST'])
def feedback():
    form=FeedbackForm()
    if current_user.is_authenticated:
        form.email.data=current_user.email
    if form.validate_on_submit():
        msg=Message('Sent by THAT Student: '+current_user.username,sender=form.email.data,recipients=['kgp.admin@gmail.com']) 
        msg.body=f'''Sent from THAT Feedback:
        {form.feedback.data}'''
        mail.send(msg)
        flash('Your message has been sent.','success')
    return render_template("feedback.html",form=form)

#--------------------------------------------------------------------------------------------
@application.route("/speechAsisstance",methods=['GET', 'POST'])
def speechAsisstance():
    return render_template("speechAsisstance.html") 


@application.route("/speechAsisstance_RoS")
def speechAsisstance_RoS():
    print("Starting Recording\n")
    average_RoS, words_in_speech, text = getRoS()
    string3 = str(words_in_speech) + " words"
    string4 = str(average_RoS) + " words/min" 
    message1 = "<h3>" +str(average_RoS) + " words/min</h3>" 
    message2 = "<h5 class=\"mb-6\">You said        : <span class=\"text-muted h5 font-weight-normal\">" + text + "<br></span></h5>"
    message3 = "<h5 class=\"mb-6\">Words in Speech : <span class=\"text-muted h5 font-weight-normal\">" + string3 + "<br></></h5>"
    message4 = "<h5 class=\"mb-6\">Rate of Speech  : <span class=\"text-muted h5 font-weight-normal\">" + string4 + "<br></></h5>"
    
    ret_val = jsonify(message1 =message1, message2= message2 ,message3=message3,message4=message4)
    return ret_val

#--------------------------------------------------------------------------------------------
# Devarshi Functions
#--------------------------------------------------------------------------------------------
@application.route("/transcripts",methods=['GET', 'POST'])
def transcripts():
    if current_user.user_type == 'Professor':
        lectures=Lecture.query.filter_by(user_id=current_user.id).all()
    else:
        lectures=Lecture.query.all()
        
    lectures.reverse()
    return render_template("transcripts.html",lectures=lectures) 

@application.route("/generate_subtitles/<int:lecture_id>", methods=['GET'])
@login_required
def generate_subtitles(lecture_id):
    lecture = Lecture.query.get_or_404(lecture_id)
    
    # Log for debugging
    print(f"Generating subtitles for lecture {lecture_id}, current subtitle_path: {lecture.subtitle_path}")
    
    # Check if subtitle path already exists
    if lecture.subtitle_path and os.path.exists(os.path.join('THAT/static', lecture.subtitle_path.replace('\\', '/'))):
        # Try to use .vtt file instead of .srt if available
        vtt_path = lecture.subtitle_path.replace('.srt', '.vtt')
        if os.path.exists(os.path.join('THAT/static', vtt_path.replace('\\', '/'))):
            print(f"Using existing VTT file: {vtt_path}")
            return jsonify({
                'success': True,
                'srt_url': url_for('static', filename=vtt_path.replace('\\', '/'))
            })
        
        # Fallback to using SRT
        print(f"Using existing SRT file: {lecture.subtitle_path}")
        return jsonify({
            'success': True,
            'srt_url': url_for('static', filename=lecture.subtitle_path.replace('\\', '/'))
        })
    
    # If subtitle path is not available, try to generate it
    video_path = os.path.join('THAT/static', lecture.video_path.replace('\\', '/'))
    print(f"Video path for subtitle generation: {video_path}")
    
    if not os.path.exists(video_path):
        print(f"Error: Video file not found at {video_path}")
        return jsonify({'success': False, 'error': 'Video file not found'})
    
    # Generate SRT path
    base_name = os.path.splitext(os.path.basename(lecture.video_path))[0]
    srt_filename = f"{base_name}.srt"
    vtt_filename = f"{base_name}.vtt"
    srt_path = os.path.join('video', srt_filename)
    vtt_path = os.path.join('video', vtt_filename)
    full_srt_path = os.path.join('THAT/static', srt_path.replace('\\', '/'))
    full_vtt_path = os.path.join('THAT/static', vtt_path.replace('\\', '/'))
    
    # Check if VTT already exists
    if os.path.exists(full_vtt_path):
        print(f"Found existing VTT file at {full_vtt_path}")
        # Update lecture record if needed
        if not lecture.subtitle_path:
            lecture.subtitle_path = srt_path  # We still store the .srt path in the database
            db.session.commit()
        
        return jsonify({
            'success': True,
            'srt_url': url_for('static', filename=vtt_path.replace('\\', '/'))
        })
    
    # Check if SRT already exists
    if os.path.exists(full_srt_path):
        print(f"Found existing SRT file at {full_srt_path}")
        # Update lecture record if needed
        if not lecture.subtitle_path:
            lecture.subtitle_path = srt_path
            db.session.commit()
        
        # Try to convert to VTT for better browser compatibility
        try:
            with open(full_srt_path, 'r', encoding='utf-8') as srt_file:
                content = srt_file.read()
            
            with open(full_vtt_path, 'w', encoding='utf-8') as vtt_file:
                vtt_file.write("WEBVTT\n\n")
                # Convert SRT to VTT by replacing comma with dot in timestamps
                content = content.replace(',', '.')
                vtt_file.write(content)
            
            print(f"Converted SRT to VTT: {full_vtt_path}")
            return jsonify({
                'success': True,
                'srt_url': url_for('static', filename=vtt_path.replace('\\', '/'))
            })
        except Exception as e:
            print(f"Error converting SRT to VTT: {str(e)}")
            # Fall back to SRT
            return jsonify({
                'success': True,
                'srt_url': url_for('static', filename=srt_path.replace('\\', '/'))
            })
    
    # Generate SRT file if it doesn't exist
    try:
        print(f"Generating new subtitle file for {video_path}")
        result = makesrt(video_path, full_srt_path)
        
        if isinstance(result, str) and result.startswith("Error"):
            print(f"Error generating subtitles: {result}")
            return jsonify({'success': False, 'error': result})
        
        # Update the lecture record with the subtitle path
        lecture.subtitle_path = srt_path
        db.session.commit()
        
        # Check which file to serve (prefer VTT)
        if os.path.exists(full_vtt_path):
            print(f"Using generated VTT file: {full_vtt_path}")
            return jsonify({
                'success': True,
                'srt_url': url_for('static', filename=vtt_path.replace('\\', '/'))
            })
        else:
            print(f"Using generated SRT file: {full_srt_path}")
            return jsonify({
                'success': True,
                'srt_url': url_for('static', filename=srt_path.replace('\\', '/'))
            })
    except Exception as e:
        print(f"Exception generating subtitles: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@application.route("/getranscripts/<int:lecture_id>",methods=['GET', 'POST'])
def getranscripts(lecture_id):
    lecture = Lecture.query.get_or_404(lecture_id)
    path = 'THAT/static/' + lecture.video_path.replace('\\', '/')
    print(path)
    transcript = getTranscript(path)
    transcript = "<h4 id=\"Transcripts\" style=\"font-size: medium;font-family: 'Courier New', Courier, monospace;\">" + str(transcript) + "</h4>"  
    ret_val = jsonify(message=transcript)
    return ret_val


@application.route("/video_player/ <int:lecture_id>")
@login_required
def video_player(lecture_id):
    lecture = Lecture.query.get_or_404(lecture_id)
    
    # Check if the subtitle path exists and update if necessary
    if lecture.subtitle_path:
        # Check if the subtitle file exists
        srt_path = os.path.join('THAT/static', lecture.subtitle_path.replace('\\', '/'))
        vtt_path = srt_path.replace('.srt', '.vtt')
        
        if not os.path.exists(srt_path) and not os.path.exists(vtt_path):
            # Subtitle files don't exist, clear the path
            print(f"Warning: Subtitle files not found for lecture {lecture_id}")
            lecture.subtitle_path = None
            db.session.commit()
        elif os.path.exists(vtt_path) and not lecture.subtitle_path.endswith('.vtt'):
            # Update to use VTT instead of SRT if available
            lecture.subtitle_path = lecture.subtitle_path.replace('.srt', '.vtt')
            db.session.commit()
            print(f"Updated lecture {lecture_id} to use VTT subtitles")
    
    print(f"Serving video {lecture.video_path} with subtitle path {lecture.subtitle_path}")
    return render_template('video_player.html', title=lecture.title, lecture=lecture)

    
@application.route("/video_transcripts/ <int:lecture_id>",methods=['GET', 'POST'])
@login_required
def video_transcripts(lecture_id):
    lecture=Lecture.query.get_or_404(lecture_id) #get_or_404 returns the requested page if it exists else it returns a 404 error
    return render_template('video_transcripts.html',title=lecture.title,lecture=lecture)


@application.route("/chat", methods=['GET', 'POST'])
@login_required
def chat():
    return render_template('chat.html', title='Chat Assistant')

@application.route("/get_chat_response", methods=['POST'])
@login_required
def get_chat_response():
    try:
        user_message = request.json.get('message', '')
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{
                "role": "user",
                "content": user_message
            }],
            max_tokens=150,
            temperature=0.7,
        )
        return jsonify({
            'success': True,
            'response': response['choices'][0]['message']['content'].strip()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
#--------------------------------------------------------------------------------------------