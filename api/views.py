from django.shortcuts import render
from collections import Counter

from django.http import JsonResponse
from .models import *
from django.db.models import Max
from datetime import date, timedelta

def calculate_gender_composition(queryset):

    genders = ['Male', 'Female', 'Other', 'I prefer not to say']
    gender_composition = {}
    respondents = 1

    for gender in genders:
        count = queryset.filter(gender=gender).count()
        gender_composition[gender] =  round((count/respondents) * 100, 1) if respondents else 0
    
    return gender_composition

def calculate_age(birthdate):

    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

def calculate_age_composition(queryset):

    respondents = queryset.count()

    # Initialize age counts
    age_counts = {
        '0-14': 0,
        '15-21': 0,
        '22-29': 0,
        '30-39': 0,
        '40-59': 0,
        'Over 60': 0,
    }

    # Calculate ages and increment corresponding age range counts
    for person in queryset:
        age = calculate_age(person.date_of_birth)
        if age <= 14:
            age_counts['0-14'] += 1
        elif 15 <= age <= 21:
            age_counts['15-21'] += 1
        elif 22 <= age <= 29:
            age_counts['22-29'] += 1
        elif 30 <= age <= 39:
            age_counts['30-39'] += 1
        elif 40 <= age <= 59:
            age_counts['40-59'] += 1
        else:  # Over 60
            age_counts['Over 60'] += 1

    age_composition = {age_range: round((count / respondents) * 100, 1) if respondents else 0 for age_range, count in age_counts.items()}

    return age_composition

def get_community(request, communityid):
    
    try:
        respondents = Person.objects.filter(communityid=communityid).count()

        most_recent_response = Response.objects.filter(
            personid__communityid=communityid
        ).aggregate(response_timestamp=Max('responsetimestamp'))['response_timestamp']

        survey_data = []
        
        surveys = Survey.objects.all()

        for survey in surveys:
            unique_respondents_count = Response.objects.filter(
                surveyquestionid__surveyid=survey.surveyid, 
                personid__communityid=communityid
            ).values('personid').distinct().count()

            person_ids = Person.objects.filter(communityid=communityid).values_list('personid', flat=True)

            number_of_responses = Response.objects.filter(
                surveyquestionid__surveyid=survey.surveyid,  # Assuming surveyquestion_ids is a list of relevant survey question IDs
                personid__in=person_ids
            ).values(
                'personid', 'surveyquestionid__surveyid'  # This fetches the surveyid through the surveyquestionid foreign key
            ).distinct().count()

            response_rate = round((number_of_responses/respondents)*100, 1) if respondents else 0

            def retrieve_answers(surveyquestionid, question_type):
            
                # Filter responses by surveyquestionid and personid being in the list of person_ids
                responses = Response.objects.filter(surveyquestionid=surveyquestionid, personid__in=person_ids)
                
                # For multiple choice questions, use a counter to tally option selections
                if question_type == 'Multiple Choice':
                    # Initialize a counter to keep track of option selections
                    frequency = Counter()

                    for response in responses:
                        selected_options = response.responsedata.split(',')
                        frequency.update(selected_options)

                    # Convert option IDs back to their texts
                    option_ids = [int(option_id) for option_id in frequency.keys()]
                    selected_options = Option.objects.filter(optionid__in=option_ids)
                    option_text = {option.optionid: option.optiontext for option in selected_options}

                    # Prepare the answer list using the counter and option texts
                    answers = [{'answer': option_text[int(option_id)], 'total': count} for option_id, count in frequency.items()]
                else:
                    answers = [{'answer': response.responsedata, 'total': 1} for response in responses]

                return answers

            questiondict = []
            surveyquestions = Surveyquestion.objects.filter(surveyid=survey.surveyid)

            for surveyquestion in surveyquestions:
                question = surveyquestion.questionid
                question_id = question.questionid
                options_count = Questionoption.objects.filter(questionid=question_id).count()

                if question.type == 'Text Entry':
                    chartType = 'text'
                elif options_count <= 4:
                    chartType = 'bar'
                else:
                    chartType = 'pie'

                question_dict = {
                    'questionid': question_id,
                    'question': question.question,
                    'chartType': chartType,
                    'answers':retrieve_answers(surveyquestion.surveyquestionid, question.type),
                }
                questiondict.append(question_dict)

            survey_dict = {
                'surveyid': survey.surveyid,
                'title': survey.title,
                'description': survey.description,
                'responseRate': response_rate,
                'responses': questiondict,
            }
            survey_data.append(survey_dict)

        community = Community.objects.get(communityid=communityid)
        gender_composition = calculate_gender_composition(Person.objects.filter(communityid=communityid))
        age_composition = calculate_age_composition(Person.objects.filter(communityid=communityid))
        
        data = {
            'communityInfo': {
                'id': communityid,
                'region': community.region,
                'country': community.countryid.name,
                'responders': respondents,
                'lastResponseDate': most_recent_response,
                'genderRatio': {
                    'male': gender_composition['Male'],
                    'female': gender_composition['Female'],                    
                },
                'ageDistribution': [
                    {'ageGroup': '0-14', 'percentage': age_composition['0-14']},
                    {'ageGroup': '15-21', 'percentage': age_composition['15-21']},
                    {'ageGroup': '22-29', 'percentage': age_composition['22-29']},
                    {'ageGroup': '30-39', 'percentage': age_composition['30-39']},
                    {'ageGroup': '40-59', 'percentage': age_composition['40-59']},
                    {'ageGroup': '60+', 'percentage': age_composition['Over 60']},
                ],
            },
            'surveyInfo': survey_data,
        }

        return JsonResponse(data)

    except Community.DoesNotExist:
        return JsonResponse({'error': 'Community not found'}, status=404)
    
def get_communities(request):

    communities = Community.objects.select_related('countryid').all() 
    data = [
        {"id": community.communityid, "region": community.region, "country": community.countryid.name}
        for community in communities
    ]

    return JsonResponse(data, safe=False)

def survey_statistics(request):

    all_people = Person.objects.all()
    age_composition = calculate_age_composition(all_people)
    total_responses = Response.objects.all().count()
    
    number_of_responses = 0
    for survey in Survey.objects.all():
        number_of_responses += Response.objects.filter(
            surveyquestionid__surveyid=survey.surveyid, 
            personid__in=all_people
        ).values(
            'personid', 'surveyquestionid__surveyid'  # This fetches the surveyid through the surveyquestionid foreign key
        ).distinct().count()

    number_of_countries = Person.objects.values_list('communityid__countryid', flat=True).distinct().count()

    statistics = {
        'totalResponses': number_of_responses,
        'totalRespondants': all_people.count(),
        'numberofCountries': number_of_countries,
        'ageDistribution': [
            {'ageGroup': '0-14', 'percentage': age_composition['0-14']},
            {'ageGroup': '15-21', 'percentage': age_composition['15-21']},
            {'ageGroup': '22-29', 'percentage': age_composition['22-29']},
            {'ageGroup': '30-39', 'percentage': age_composition['30-39']},
            {'ageGroup': '40-59', 'percentage': age_composition['40-59']},
            {'ageGroup': '60+', 'percentage': age_composition['Over 60']},
        ],
    }

    return JsonResponse(statistics, safe=False)

def get_countries(request):
    countryList = []

    # Get all country IDs that exist in the Community table
    country_ids = Community.objects.values_list('countryid', flat=True).distinct()
    # Use those IDs to filter Country instances
    countries = Country.objects.filter(countryid__in=country_ids)

    for country in countries:
        communities = Community.objects.filter(countryid=country.countryid)
        respondents = 0
        for community in communities:
            respondents += Person.objects.filter(communityid=community.communityid).count()        
        
        countryInfo = {
            'code': country.code,
            'country': country.name,
            'latitude': country.latitude, 
            'longitude': country.longitude, 
            'regionNumber': country.countryid, 
            'respondants': respondents,
        }

        countryList.append(countryInfo)

    return JsonResponse(countryList, safe=False)

def get_country(request, countrycode):

    try:
        
        country = Country.objects.get(code=countrycode)
        number_of_regions = Community.objects.filter(countryid=country.countryid).distinct().count()
        
        community_ids = Community.objects.filter(countryid=country.countryid).values_list('communityid', flat=True)
        respondents = 0
        for community in Community.objects.filter(communityid__in=community_ids):
            respondents += Person.objects.filter(communityid=community.communityid).count()   
        
        people = Person.objects.filter(communityid__in=community_ids)
        age_composition = calculate_age_composition(people)
        most_recent_response = Response.objects.filter(personid__in=people).order_by('-responsetimestamp').first()

        # Extract the timestamp if a response exists, else default to None or a suitable placeholder.
        most_recent_response_date = most_recent_response.responsetimestamp if most_recent_response else 'No responses'

        gender_composition = calculate_gender_composition(people)

        countryRegions = []
        for community in Community.objects.filter(communityid__in=community_ids):
            person_ids = Person.objects.filter(communityid=community.communityid).values_list('personid', flat=True)
            number_of_responses = 0
            for survey in Survey.objects.all():
                number_of_responses += Response.objects.filter(
                    surveyquestionid__surveyid=survey.surveyid, 
                    personid__in=person_ids
                ).values(
                    'personid', 'surveyquestionid__surveyid'  # This fetches the surveyid through the surveyquestionid foreign key
                ).distinct().count()

            community_info = {
                'id': community.communityid,
                'region': community.region,
                'responses': number_of_responses
            }
            countryRegions.append(community_info)

        countryResponse = {
            'countryInfo': {
                'code': countrycode,
                'countryName': country.name,
                'respondents': respondents,
                'regions': number_of_regions,
                'lastResponseDate': most_recent_response_date.strftime("%B %d, %Y") if most_recent_response else most_recent_response_date,
                'genderRatio': {
                    'male': gender_composition['Male'],
                    'female': gender_composition['Female'],
                },
                'ageDistribution': [
                    {'ageGroup': '0-14', 'percentage': age_composition['0-14']},
                    {'ageGroup': '15-21', 'percentage': age_composition['15-21']},
                    {'ageGroup': '22-29', 'percentage': age_composition['22-29']},
                    {'ageGroup': '30-39', 'percentage': age_composition['30-39']},
                    {'ageGroup': '40-59', 'percentage': age_composition['40-59']},
                    {'ageGroup': '60+', 'percentage': age_composition['Over 60']},
                ],
            },
            'countryRegions': countryRegions,
        }

        return JsonResponse(countryResponse, safe=False)
    
    except Country.DoesNotExist:
        return JsonResponse({'error': 'Country not found'}, status=404)