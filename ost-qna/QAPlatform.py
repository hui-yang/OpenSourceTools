import os
import urllib
from google.appengine.api import images
from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.datastore.datastore_query import Cursor

from google.appengine.ext import blobstore
from google.appengine.ext.blobstore import BlobInfo
from google.appengine.ext.webapp import blobstore_handlers
import jinja2
import webapp2
import logging

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

# models
class Question(ndb.Model):
    name = ndb.StringProperty()
    content = ndb.TextProperty()
    author = ndb.UserProperty()
    #    image = ndb.BlobProperty(indexed=False)
    #    imageUrl = ndb.StringProperty(indexed=False)
    tags = ndb.StringProperty(indexed=True,repeated=True)
    createtime = ndb.DateTimeProperty(auto_now_add=True)
    modtime = ndb.DateTimeProperty(auto_now=True)
    ups = ndb.IntegerProperty()
    downs = ndb.IntegerProperty()
    net = ndb.IntegerProperty()
    
class Answer(ndb.Model):
    name = ndb.StringProperty()
    content = ndb.TextProperty()
    author = ndb.UserProperty()
    #    image = ndb.BlobProperty(indexed=False)
    #    imageUrl = ndb.StringProperty(indexed=False)
    createtime = ndb.DateTimeProperty(auto_now_add=True)
    modtime = ndb.DateTimeProperty(auto_now=True)
    ups = ndb.IntegerProperty()
    downs = ndb.IntegerProperty()
    net = ndb.IntegerProperty()

class Vote(ndb.Model):
    value = ndb.BooleanProperty()
    vtype = ndb.StringProperty() # question / answer
    author = ndb.UserProperty()
    
class Image(ndb.Model):
    author = ndb.UserProperty()
    img = ndb.BlobKeyProperty(indexed=False)
    imgUrl = ndb.StringProperty()
    createtime = ndb.DateTimeProperty(auto_now_add=True)

# filters
def img_inline(string):
    str = re.sub(r'(\http[s]?://[^\s<>"]+|www\.[^\s<>"]+)', r'<a href="\1">\1</a>', string)
    str1 = re.sub(r'<a href="(\http[s]?://[^\s<>"]+|www\.[^\s<>"]+)">[^\s]+.jpg</a>', r'<img src="\1">', str)
    str2 = re.sub(r'<a href="(\http[s]?://[^\s<>"]+|www\.[^\s<>"]+)">[^\s]+.png</a>', r'<img src="\1">', str1)
    str3 = re.sub(r'<a href="(\http[s]?://[^\s<>"]+|www\.[^\s<>"]+)">[^\s]+.gif</a>', r'<img src="\1">', str2)
    return str3
jinja2.filters.FILTERS['img_inline'] = img_inline

# request handlers
class MainPage(webapp2.RequestHandler):
    def get(self):
        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
            
        cursor = Cursor(urlsafe=self.request.get('cursor'))
        questions, next_cursor, more = Question.query().order(-Question.modtime).fetch_page(10, start_cursor=cursor)
        """
        questiondeletes=Question.query().fetch()
        for questiondelete in questiondeletes:
            questiondelete.key.delete() 
                 
        adelete = Answer.query().fetch()
        for ad in adelete:
            ad.key.delete()
            
        votedelete = Vote.query().fetch()
        for vd in votedelete:
            vd.key.delete()
        """
                
        template_values = {
                'url': url,
                'url_linktext': url_linktext,
                'questions': questions,
                'nextpage': ''
        }
        if more and next_cursor:
            template_values['nextpage'] = next_cursor.urlsafe()
            
        template = JINJA_ENVIRONMENT.get_template('MainPage.html')
        self.response.write(template.render(template_values))
# end of MainPage

class AddQuestion(webapp2.RequestHandler):
    def get(self):
        if users.get_current_user():
            user = users.get_current_user()
        else:
            self.redirect(users.create_login_url(self.request.uri))
        
        template_values = {
                'user':users.get_current_user(),
                'url_linktext': 'Logout',
                'url': users.create_logout_url(self.request.uri)
        }
        
        if self.request.get('questionID'):
            qid = self.request.get('questionID')
            question = ndb.Key(urlsafe=qid).get()
            template_values['question']=question
            
        template = JINJA_ENVIRONMENT.get_template('AddQuestion.html')
        self.response.write(template.render(template_values))
    def post(self):
        if self.request.get('questionID'):
            qid = self.request.get('questionID')
            question = ndb.Key(urlsafe=qid).get()
        else:
            question = Question()
        question.author = users.get_current_user()
        question.name = self.request.get('name')
        question.content = self.request.get('content')
        question.tags = self.request.get('tags', allow_multiple = True)
        question.ups = 0
        question.downs = 0
        question.net = 0
        question.put()
        url='/ViewQuestion?questionID=%s' % question.key.urlsafe()
        self.redirect(url)

class AddAnswer(webapp2.RedirectHandler): # add and edit
    def get(self):
        if users.get_current_user():
            user = users.get_current_user()
        else:
            self.redirect(users.create_login_url(self.request.uri))
        
        questionID = self.request.get('questionID')

        template_values = {
            'user': users.get_current_user(),
            'url_linktext': 'Logout',
            'url': users.create_login_url(self.request.uri),
            'questionID': questionID,
        }
        
        if self.request.get('answerID'):
            answerID = self.request.get('answerID')
            answer = ndb.Key(urlsafe=answerID).get()
            template_values = {
                'answer': answer,
            }
            
        template = JINJA_ENVIRONMENT.get_template('Answer.html')
        self.response.write(template.render(template_values))
    def post(self):
        qid = self.request.get('questionID')
        question = ndb.Key(urlsafe = qid).get()
        
        if self.request.get('answerID'):
            aid = self.request.get('answerID')
            answer = ndb.Key(urlsafe = aid).get()
        else:
            answer = Answer(parent=question.key)

        answer.author = users.get_current_user()
        answer.name = self.request.get('name')
        answer.content = self.request.get('content')
        answer.ups = 0
        answer.downs = 0
        answer.net = 0
        answer.put()
        url='/ViewQuestion?questionID=%s' % qid
        self.redirect(url)

class ViewQuestion(webapp2.RequestHandler):
    def get(self):
        if self.request.get('questionID'):
            user = users.get_current_user()
            questionID = self.request.get('questionID')
            question = ndb.Key(urlsafe = questionID).get()
            
            answers = Answer.query(ancestor = question.key).order(-Answer.net).fetch()
            
            template_values = {
                'question': question,
                'answers': answers,
                'user': user,
            }
            template = JINJA_ENVIRONMENT.get_template('ViewQuestion.html')
            self.response.write(template.render(template_values))
            
class VoteQ(webapp2.RequestHandler):
    def get(self):
        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
            
        questionID = self.request.get("questionID")
        question = ndb.Key(urlsafe = questionID).get()
        
        value = self.request.get("value")   
        cur_user = users.get_current_user()
        
        oldvote = Vote.query(Vote.author==cur_user, Vote.vtype=="question", ancestor=ndb.Key(urlsafe = questionID)).get()
        if oldvote:
            if oldvote.value == False and value == "true":
                oldvote.value = True
                question.net +=2
                question.ups += 1
                question.downs -= 1
            elif oldvote.value == True and value == "false":
                oldvote.value = False
                question.net -=2
                question.ups -= 1
                question.downs += 1
            question.put()
            oldvote.put()
        else:
            vote = Vote(parent=ndb.Key(urlsafe = questionID))
            if value == "true":
                question.net += 1
                question.ups += 1
                vote.value = True
            else:
                question.net -= 1
                question.downs += 1
                vote.value = False
            question.put()      
            vote.vtype = "question"
            vote.author = cur_user
            vote.put()
        urlquestion='/ViewQuestion?questionID=%s' % questionID
        self.redirect(urlquestion)

class VoteA(webapp2.RequestHandler):
    def get(self):
        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
            
        questionID = self.request.get("questionID")
        question = ndb.Key(urlsafe = questionID).get()
        answerID = self.request.get("answerID")
        answer = ndb.Key(urlsafe = answerID).get()
        
        value = self.request.get("value")
        
        cur_user = users.get_current_user()
        
        oldvote = Vote.query(Vote.author==cur_user, Vote.vtype == "answer", ancestor = answer.key).get()
        if oldvote:
            if oldvote.value == False and value == "true":
                answer.net +=2
                answer.ups += 1
                answer.downs -= 1
                answer.put()
                    
                oldvote.value = True
                oldvote.put()
            elif oldvote.value == True and value == "false":
                answer.net -=2
                answer.ups -= 1
                answer.downs += 1
                answer.put()
                    
                oldvote.value = False
                oldvote.put()
        else:
            vote = Vote(parent = answer.key)
            if value == "true":
                answer.net += 1
                answer.ups += 1
                vote.value = True
            else:
                answer.net -= 1
                answer.downs += 1
                vote.value = False 
            answer.put()
            
            vote.vtype = "answer"
            vote.author = cur_user
            vote.put()
        urlquestion='/ViewQuestion?questionID=%s' % questionID
        self.redirect(urlquestion)

class UploadImage(blobstore_handlers.BlobstoreUploadHandler):
    def get(self):
        if users.get_current_user():
            user = users.get_current_user()
        else:
            self.redirect(users.create_login_url(self.request.uri))
        upload_url = blobstore.create_upload_url('/UploadImage')
        template_values = {
                'user':users.get_current_user(),
                'url_linktext': 'Logout',
                'url': users.create_logout_url(self.request.uri),
                'uploadurl': upload_url,
        }
        template = JINJA_ENVIRONMENT.get_template('UploadImg.html')
        self.response.write(template.render(template_values))
        
    def post(self):
        image = Image()
        imgfile = self.get_uploads('image')
        if imgfile:
            blob_info = imgfile[0]
            image.img = blob_info.key()
            image.author = users.get_current_user()
            image.imgUrl = images.get_serving_url(blob_info.key())
            image.put()
        self.redirect('/')
        
# interface
application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/AddQuestion', AddQuestion),
    ('/AddAnswer', AddAnswer),
    ('/ViewQuestion', ViewQuestion),
    ('/VoteQ', VoteQ),
    ('/VoteA', VoteA),
    ('/UploadImage', UploadImage),
], debug=True)