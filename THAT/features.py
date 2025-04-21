#--------------------------------------------------------------------------------------------------------------------- 
# Feature 3 : Rate of Speech
#---------------------------------------------------------------------------------------------------------------------
import time
import string
import pyaudio
import speech_recognition as sr
from plyer import notification 
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER
from nltk.tokenize import sent_tokenize, word_tokenize 
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

#--------------------------------------------------------------------------------------------------------------------- 
# Utility Function to convert speech to text
#---------------------------------------------------------------------------------------------------------------------
def recognize_speech_from_mic(recognizer, microphone):
    if not isinstance(recognizer, sr.Recognizer):
        raise TypeError("`recognizer` must be `Recognizer` instance")

    if not isinstance(microphone, sr.Microphone):
        raise TypeError("`microphone` must be `Microphone` instance")

    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
      
    response = {"success": True,"error": None,"transcription": None}

    try:
        response["transcription"] = recognizer.recognize_google(audio)
    except sr.RequestError:
        response["success"] = False
        response["error"] = "API unavailable"
    except sr.UnknownValueError:
        response["error"] = "Unable to recognize speech"

    return response

#------------------------------------------------------------------------------------------------------------------- 
# Function  -> perform_this_task(latency, wait_parameter, start_time, array_RoS)
# Arguments -> latency : specifies amount of time to be reduced to compensate start & end time delay during recording
#              wait_parameter : specifies number of consecutives iterations to wait before stopping recording
#              start_time     : specifies time when function is called
#              array_RoS      : Array to store the rate of speech of each iteration
# Returns   -> Array with rate of speech of each iteration
#------------------------------------------------------------------------------------------------------------------- 
def perform_this_task(latency,wait_parameter, start_time,array_RoS):
    wait_count=0
    text=""
    while 1:
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        guess = recognize_speech_from_mic(recognizer, microphone)

        if guess["transcription"] == None:
            print("\n\nYou are not speaking...okay then bye")
            if wait_count < wait_parameter:
                wait_count = wait_count + 1   
                continue
            else:
                return

        wait_count = 0
        text=text+ guess["transcription"] 
        time_of_speech = time.time() - start_time - latency   #Subtracting latency
        words_in_speech = sum([i.strip(string.punctuation).isalpha() for i in guess["transcription"].split()])
        rate_of_speech = (words_in_speech*60)/ time_of_speech

        # Printing messages to test results. Comment the lines after final testing.
        print("\nYou said      : ",guess["transcription"])
        print("Words in speech : ", words_in_speech) 
        print("Time Taken      : ", str(round(time_of_speech,2))+" seconds.")      
        print("Rate of Speech  : " + str(round(rate_of_speech,2)) +" WPM.\n") # Rate of speech in Words per minute

        array_RoS.append(round(rate_of_speech,2))
        return array_RoS, words_in_speech, text        

#--------------------------------------------------------------------------------------------------------------------- 
# Main Function -> Will be called when user hits the start button in RoS Feature
# Returns       -> Average rate of speech & Array with rate of speech of each iteration
#---------------------------------------------------------------------------------------------------------------------
def getRoS():
    array_RoS = list()
    average_RoS = 0
    array_RoS,words_in_speech, text = perform_this_task(3,0,time.time(),array_RoS)
    
    if array_RoS != None:
        for ros in array_RoS:
            average_RoS = average_RoS + ros
        average_RoS = average_RoS / len(array_RoS)
        
    return average_RoS, str(words_in_speech), text  


#--------------------------------------------------------------------------------------------------------------------- 
# Feature 2 : Lecture Transcripts
#---------------------------------------------------------------------------------------------------------------------

import os
from os import path
import moviepy.editor as mp
#--------------------------------------------------------------------------------------------------------------------- 
# Function -> convertmp4towav 
# Returns  -> video path
#---------------------------------------------------------------------------------------------------------------------
def convertmp4towav(path) :
    clip = mp.VideoFileClip(path)
    clip.audio.write_audiofile("video.wav",codec='pcm_s16le')
    return "video.wav"

#--------------------------------------------------------------------------------------------------------------------- 
# Function -> getTranscript 
# Returns  -> string (Transcript)
#---------------------------------------------------------------------------------------------------------------------
def getTranscript(path):
    try:
        # Check if file exists
        if not os.path.exists(path):
            return "Error: Video file not found"
            
        text = ""
        filename = convertmp4towav(path)
        r = sr.Recognizer()
        
        # Check if wav file was created successfully
        if not os.path.exists(filename):
            return "Error: Could not convert video to audio"
            
        with sr.AudioFile(filename) as source:
            audio = r.record(source)
            
        try:
            text = r.recognize_google(audio)
        except sr.UnknownValueError:
            text = "Error: Speech could not be recognized"
        except sr.RequestError as e:
            text = f"Error: Could not request results from speech recognition service; {str(e)}"
        
        # Clean up temporary wav file
        if os.path.exists(filename):
            os.remove(filename)
            
        return text
        
    except Exception as e:
        return f"Error: {str(e)}"

#--------------------------------------------------------------------------------------------------------------------- 
# Feature 1 : Live Captioning
#---------------------------------------------------------------------------------------------------------------------


#--------------------------------------------------------------------------------------------------------------------- 
# Function : makesrt
# Streams captions
#---------------------------------------------------------------------------------------------------------------------
def makesrt(video_path, output_path=None):
    """
    Creates an SRT subtitle file from a video file.
    
    Parameters:
        video_path (str): Path to the video file
        output_path (str, optional): Path where SRT file will be saved. If None, saves to the same directory with same name as video but .srt extension.
    
    Returns:
        str: Path to the created SRT file or error message
    """
    try:
        # Check if file exists
        if not os.path.exists(video_path):
            return "Error: Video file not found"
            
        # If output path is not specified, use video filename with .srt extension
        if output_path is None:
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(os.path.dirname(video_path), f"{base_name}.srt")
        
        # Define VTT path - always create both formats
        vtt_output_path = output_path.replace('.srt', '.vtt')
        
        # Convert video to audio
        wav_filename = convertmp4towav(video_path)
        
        # Check if wav file was created successfully
        if not os.path.exists(wav_filename):
            return "Error: Could not convert video to audio"
            
        r = sr.Recognizer()
        
        # Process audio in chunks to get timestamps
        with sr.AudioFile(wav_filename) as source:
            # Get audio duration
            audio_duration = mp.AudioFileClip(wav_filename).duration
            
            # Determine chunk size (in seconds)
            chunk_duration = 10  # 10-second chunks
            
            # Create SRT file
            with open(output_path, 'w', encoding='utf-8') as srt_file:
                chunk_count = 0
                
                # Process audio in chunks for SRT
                for start_time in range(0, int(audio_duration), chunk_duration):
                    chunk_count += 1
                    
                    # Get end time for this chunk
                    end_time = min(start_time + chunk_duration, audio_duration)
                    
                    # Set position in audio file
                    source.position = start_time
                    
                    # Listen to chunk
                    chunk_audio = r.record(source, duration=min(chunk_duration, end_time - start_time))
                    
                    try:
                        # Recognize speech in chunk
                        text = r.recognize_google(chunk_audio)
                        
                        if text:
                            # Format times for SRT (HH:MM:SS,mmm)
                            start_formatted = time.strftime('%H:%M:%S,000', time.gmtime(start_time))
                            end_formatted = time.strftime('%H:%M:%S,000', time.gmtime(end_time))
                            
                            # Write subtitle entry (SRT format)
                            srt_file.write(f"{chunk_count}\n")
                            srt_file.write(f"{start_formatted} --> {end_formatted}\n")
                            srt_file.write(f"{text}\n\n")
                    
                    except sr.UnknownValueError:
                        # No speech detected in this chunk, skip
                        continue
                    except sr.RequestError:
                        # API error, log but continue
                        print(f"Could not request results for chunk at {start_time}s")
                        continue
            
            # Create WebVTT file
            with open(vtt_output_path, 'w', encoding='utf-8') as vtt_file:
                vtt_file.write("WEBVTT\n\n")
                chunk_count = 0
                
                # Reset for second pass
                source.position = 0
                
                # Process audio in chunks for WebVTT
                for start_time in range(0, int(audio_duration), chunk_duration):
                    chunk_count += 1
                    
                    # Get end time for this chunk
                    end_time = min(start_time + chunk_duration, audio_duration)
                    
                    # Set position in audio file
                    source.position = start_time
                    
                    # Listen to chunk
                    chunk_audio = r.record(source, duration=min(chunk_duration, end_time - start_time))
                    
                    try:
                        # Recognize speech in chunk
                        text = r.recognize_google(chunk_audio)
                        
                        if text:
                            # Format times for WebVTT (HH:MM:SS.mmm)
                            start_formatted = time.strftime('%H:%M:%S.000', time.gmtime(start_time))
                            end_formatted = time.strftime('%H:%M:%S.000', time.gmtime(end_time))
                            
                            # Write subtitle entry (WebVTT format)
                            vtt_file.write(f"{start_formatted} --> {end_formatted}\n")
                            vtt_file.write(f"{text}\n\n")
                    
                    except sr.UnknownValueError:
                        # No speech detected in this chunk, skip
                        continue
                    except sr.RequestError:
                        # API error, log but continue
                        print(f"Could not request results for chunk at {start_time}s")
                        continue
        
        # Clean up temporary wav file
        if os.path.exists(wav_filename):
            os.remove(wav_filename)
        
        print(f"Created subtitle files: SRT: {output_path}, VTT: {vtt_output_path}")
        return vtt_output_path  # Return VTT path as primary format
        
    except Exception as e:
        return f"Error: {str(e)}"
