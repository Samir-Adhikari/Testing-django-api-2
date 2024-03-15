from django.db import models

class Country(models.Model):
    countryid = models.AutoField(db_column='countryId', primary_key=True)  
    name = models.CharField(max_length=512, blank=True, null=True)
    code = models.CharField(max_length=512, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Country'

class Community(models.Model):
    communityid = models.AutoField(db_column='communityId', primary_key=True) 
    countryid = models.ForeignKey('Country', models.DO_NOTHING, db_column='countryId', blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Community'


class Option(models.Model):
    optionid = models.AutoField(db_column='optionId', primary_key=True) 
    optiontext = models.CharField(db_column='optionText', max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Option'


class Person(models.Model):
    personid = models.AutoField(db_column='personId', primary_key=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=50, blank=True, null=True)
    communityid = models.ForeignKey(Community, models.DO_NOTHING, db_column='communityId', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Person'


class Question(models.Model):
    questionid = models.AutoField(db_column='questionId', primary_key=True)
    type = models.CharField(max_length=50, blank=True, null=True)
    question = models.TextField(blank=True, null=True) 

    class Meta:
        managed = False
        db_table = 'Question'


class Questionoption(models.Model):
    questionoptionid = models.AutoField(db_column='questionOptionId', primary_key=True)
    questionid = models.ForeignKey(Question, models.DO_NOTHING, db_column='questionId', blank=True, null=True)
    optionid = models.ForeignKey(Option, models.DO_NOTHING, db_column='optionId', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'QuestionOption'


class Response(models.Model):
    responseid = models.AutoField(db_column='responseId', primary_key=True)
    surveyquestionid = models.ForeignKey('Surveyquestion', models.DO_NOTHING, db_column='surveyQuestionId', blank=True, null=True)
    personid = models.ForeignKey(Person, models.DO_NOTHING, db_column='personId', blank=True, null=True)
    responsedata = models.CharField(db_column='responseData', max_length=255, blank=True, null=True)
    responsetimestamp = models.DateTimeField(db_column='responseTimestamp', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Response'


class Survey(models.Model):
    surveyid = models.AutoField(db_column='surveyId', primary_key=True)
    title = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Survey'


class Surveyquestion(models.Model):
    surveyquestionid = models.AutoField(db_column='surveyQuestionId', primary_key=True)
    surveyid = models.ForeignKey(Survey, models.DO_NOTHING, db_column='surveyId', blank=True, null=True)
    questionid = models.ForeignKey(Question, models.DO_NOTHING, db_column='questionId', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'SurveyQuestion'
