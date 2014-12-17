import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.datastore.datastore_query import Cursor

import jinja2
import webapp2


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
    img = ndb.BlobProperty(indexed=False)
    imgUrl = ndb.StringProperty(indexed=False)
    createtime = ndb.DateTimeProperty(auto_now_add=True)

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
           
        """questiondeletes=Question.query().fetch()
        for questiondelete in questiondeletes:
            questiondelete.key.delete()     """ 
      
        voting = []
        for question in questions:
            ups = 0
            downs = 0
            votes = Vote.query(Vote.vtype == "question", ancestor = question.key).fetch()
            for vote in votes:
                if vote.value:
                    ups += 1
                else:
                    downs += 1
                voting.append((question, ups, downs))
                
        template_values = {
                'url': url,
                'url_linktext': url_linktext,
                'questions': questions,
                'voting': voting,
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
        answer.put()
        url='/ViewQuestion?questionID=%s' % qid
        self.redirect(url)

class ViewQuestion(webapp2.RequestHandler):
    def get(self):
        if self.request.get('questionID'):
            user = users.get_current_user()
            questionID = self.request.get('questionID')
            question = ndb.Key(urlsafe = questionID).get()
            votes = Vote.query(ancestor = question.key).fetch()
            ups = 0
            downs = 0
            for vote in votes:
                if vote.vote:
                    ups += 1
                else:
                    downs += 1
            voting = (ups, downs)
            
            answers = Answer.query(ancestor = question.key).order(-Answer.net).fetch()
            
            template_values = {
                'question': question,
                'voting': voting,
                'answers': answers,
                'user': user,
            }
            template = JINJA_ENVIRONMENT.get_template('ViewQuestion.html')
            self.response.write(template.render(template_values))
            


# interface
application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/AddQuestion', AddQuestion),
    ('/AddAnswer', AddAnswer),
    ('/ViewQuestion', ViewQuestion),
    #('/UploadImage', UploadImage),
], debug=True)