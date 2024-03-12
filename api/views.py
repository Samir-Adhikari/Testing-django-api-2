from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from .models import *
from django.db.models import Max
from datetime import date, timedelta

def get_community(request, country, city):
    try:
        community = Community.objects.get(country = country, city = city)

        respondents = (Person.objects.filter(communityid=community.communityid)).count()

        last_response_date = Response.objects.filter(
            personid__communityid=community.communityid
        ).aggregate(last_response=Max('responsetimestamp'))['last_response']

        number_of_males = (Person.objects.filter(communityid=community.communityid, gender='Male')).count()
        number_of_females = (Person.objects.filter(communityid=community.communityid, gender='Female')).count()
        number_of_others = (Person.objects.filter(communityid=community.communityid, gender='Other')).count()
        number_of_i_prefer_not_to_say = (Person.objects.filter(communityid=community.communityid, gender='I prefer not to say')).count()

        current_date = date.today()

        age_0_14 = Person.objects.filter(
            date_of_birth__gte=current_date.replace(year=current_date.year - 15) - timedelta(days=1)
        ).count()

        age_15_21 = Person.objects.filter(
            date_of_birth__range=[
                current_date.replace(year=current_date.year - 22) - timedelta(days=1),
                current_date.replace(year=current_date.year - 15)
            ]
        ).count()

        age_22_29 = Person.objects.filter(
            date_of_birth__range=[
                current_date.replace(year=current_date.year - 30)  - timedelta(days=1),
                current_date.replace(year=current_date.year - 22)
            ]
        ).count()

        age_30_39 = Person.objects.filter(
            date_of_birth__range=[
                current_date.replace(year=current_date.year - 40)  - timedelta(days=1),
                current_date.replace(year=current_date.year - 30)
            ]
        ).count()

        age_40_59 = Person.objects.filter(
            date_of_birth__range=[
                current_date.replace(year=current_date.year - 60)  - timedelta(days=1),
                current_date.replace(year=current_date.year - 40)
            ]
        ).count()

        age_over_60 = Person.objects.filter(
            date_of_birth__lte=current_date.replace(year=current_date.year - 60)
        ).count()

        survey_info = []
        surveys = Survey.objects.all()

        for survey in surveys:
            unique_respondents_count = Response.objects.filter(
                surveyquestionid__surveyid=survey.surveyid, 
                personid__communityid=community.communityid
            ).values('personid').distinct().count()
            response_rate = round((unique_respondents_count/respondents)*100,1)

            def retrieve_answers(surveyquestionid):
                responses = Response.objects.filter(surveyquestionid=surveyquestionid)
                answers_list = []
                for response in responses:
                    answers_list.append({
                        'answer': response.responsedata,
                        'total': 1,
                    })
                return answers_list

            questiondict = []
            surveyquestions = Surveyquestion.objects.filter(surveyid=survey.surveyid)
            for surveyquestion in surveyquestions:
                question = surveyquestion.questionid
                questionid = question.questionid
                question_description = question.question
                question_type = question.type
                question_dict = {
                    'questionid': questionid,
                    'question': question_description,
                    'question type': question_type,
                    'answers':retrieve_answers(surveyquestion.surveyquestionid),
                }
                questiondict.append(question_dict)

            survey_dict = {
                'surveyid': survey.surveyid,
                'title': survey.title,
                'description': survey.description,
                'responseRate': response_rate,
                'responses': questiondict,
            }
            survey_info.append(survey_dict)
        
        data = {
            'communityInfo': {
                'id': community.communityid,
                'city': community.city,
                'country': community.country,
                'respondents': respondents,
                'lastResponseDate': last_response_date,
                'genderRatio': {
                    'Male': number_of_males,
                    'Female': number_of_females,
                    'Other': number_of_others,
                    'I prefer not to say': number_of_i_prefer_not_to_say,
                },
                'ageDistribution': [
                    {'ageGroup': '0-14', 'percentage': round((age_0_14/respondents)*100,1)},
                    {'ageGroup': '15-21', 'percentage': round((age_15_21/respondents)*100,1)},
                    {'ageGroup': '22-29', 'percentage': round((age_22_29/respondents)*100,1)},
                    {'ageGroup': '30-39', 'percentage': round((age_30_39/respondents)*100,1)},
                    {'ageGroup': '40-59', 'percentage': round((age_40_59/respondents)*100,1)},
                    {'ageGroup': '60+', 'percentage': round((age_over_60/respondents)*100,1)},
                ],
            },
            'surveyInfo': survey_info,
        }
        return JsonResponse(data)
    except Community.DoesNotExist:
        return JsonResponse({'error': 'Community not found'}, status=404)