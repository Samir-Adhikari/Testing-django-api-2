from django.shortcuts import render
from collections import Counter

# Create your views here.
from django.http import JsonResponse
from .models import *
from django.db.models import Max
from datetime import date, timedelta

def count_persons_by_gender(queryset):
    """
    Count the number of persons in a community by gender.
    
    Args:
        communityid (int): ID of the community.
        
    Returns:
        dict: A dictionary containing counts of persons by gender.
            Keys are gender labels, and values are the corresponding counts.
    """
    genders = ['Male', 'Female', 'Other', 'I prefer not to say']
    counts = {}
    
    for gender in genders:
        count = queryset.filter(gender=gender).count()
        counts[gender] = count
    
    return counts

def calculate_age(birthdate):
    """Calculate age given a birthdate."""
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

def age_range_percentages(respondents, queryset=None):
    """Calculate percentages of people in various age ranges."""
    if queryset is None:
        queryset = Person.objects.all()
    
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
        age = calculate_age(person.date_of_birth)  # Assuming date_of_birth is a DateTimeField
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

    # Calculate percentages
    percentages_by_age_range = {range_label: round((count / respondents) * 100, 1) if respondents else 0 for range_label, count in age_counts.items()}

    return percentages_by_age_range

def get_community(request, communityid):
    try:
        
        # Get the count of respondents in the Person table for the given communityid
        respondents = Person.objects.filter(communityid=communityid).count()

        last_response_date = Response.objects.filter(
            personid__communityid=communityid
        ).aggregate(last_response=Max('responsetimestamp'))['last_response']

        survey_info = []
        surveys = Survey.objects.all()

        for survey in surveys:
            unique_respondents_count = Response.objects.filter(
                surveyquestionid__surveyid=survey.surveyid, 
                personid__communityid=communityid
            ).values('personid').distinct().count()
            if respondents == 0:
                response_rate = 0
            else:
                response_rate = round((unique_respondents_count/respondents)*100,1)

            def retrieve_answers(surveyquestionid, question_type):
                person_ids = Person.objects.filter(communityid=communityid).values_list('personid', flat=True)

                # Filter responses by surveyquestionid and personid being in the list of person_ids
                responses = Response.objects.filter(surveyquestionid=surveyquestionid, personid__in=person_ids)

                # For multiple choice questions, use a counter to tally option selections
                if question_type == 'Multiple Choice':
                    # Initialize a counter to keep track of option selections
                    option_counter = Counter()

                    for response in responses:
                        option_array = response.responsedata.split(',')
                        option_counter.update(option_array)

                    # Convert option IDs back to their texts
                    option_ids = [int(option_id) for option_id in option_counter.keys()]
                    options = Option.objects.filter(optionid__in=option_ids)
                    option_texts = {option.optionid: option.optiontext for option in options}

                    # Prepare the answer list using the counter and option texts
                    answers_list = [{'answer': option_texts[int(option_id)], 'total': count} for option_id, count in option_counter.items()]
                else:
                    # If not a multiple choice question, aggregate responses directly
                    answers_list = [{'answer': response.responsedata, 'total': 1} for response in responses]

                return answers_list

            questiondict = []
            surveyquestions = Surveyquestion.objects.filter(surveyid=survey.surveyid)
            for surveyquestion in surveyquestions:
                questionid = surveyquestion.questionid.questionid
                question = Question.objects.get(questionid=questionid)
                options_count = Questionoption.objects.filter(questionid=questionid).count()
                if question.type == 'Text Entry':
                    chartType = 'text'
                elif options_count <= 3:
                    chartType = 'bar'
                else:
                    chartType = 'pie'
                question_dict = {
                    'questionid': questionid,
                    'question': question.question,
                    #make dynamic
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
            survey_info.append(survey_dict)

        community = Community.objects.get(communityid=communityid)
        gender_count = count_persons_by_gender(Person.objects.filter(communityid=communityid))
        age_percentage = age_range_percentages(respondents, Person.objects.filter(communityid=communityid))
        
        data = {
            'communityInfo': {
                'id': communityid,
                'region': community.city,
                'country': community.countryid.name,
                'responders': respondents,
                'lastResponseDate': last_response_date,
                'genderRatio': {
                    'male': gender_count['Male'],
                    'female': gender_count['Female'],
                    #'Other': gender_count['Other'],
                    #'I prefer not to say': gender_count['I prefer not to say'],
                },
                'ageDistribution': [
                    {'ageGroup': '0-14', 'percentage': age_percentage['0-14']},
                    {'ageGroup': '15-21', 'percentage': age_percentage['15-21']},
                    {'ageGroup': '22-29', 'percentage': age_percentage['22-29']},
                    {'ageGroup': '30-39', 'percentage': age_percentage['30-39']},
                    {'ageGroup': '40-59', 'percentage': age_percentage['40-59']},
                    {'ageGroup': '60+', 'percentage': age_percentage['Over 60']},
                ],
            },
            'surveyInfo': survey_info,
        }
        return JsonResponse(data)
    except Community.DoesNotExist:
        return JsonResponse({'error': 'Community not found'}, status=404)
    
def get_communities(request):
    communities = Community.objects.select_related('countryid').all()  # Optimized query
    data = [
        {"id": community.communityid, "region": community.city, "country": community.countryid.name}
        for community in communities
    ]
    return JsonResponse(data, safe=False)  # Return response as JSON

def survey_statistics(request):

    total_persons = Person.objects.all().count()
    age_percentage = age_range_percentages(total_persons)
    total_responses = Response.objects.all().count()
    unique_countries_count = Person.objects.values_list('communityid__countryid', flat=True).distinct().count()
    
    statistics = {
        'totalResponses': total_responses,
        'totalRespondants': total_persons,
        'numberofCountries': unique_countries_count,
        'ageDistribution': [
            {'ageGroup': '0-14', 'percentage': age_percentage['0-14']},
            {'ageGroup': '15-21', 'percentage': age_percentage['15-21']},
            {'ageGroup': '22-29', 'percentage': age_percentage['22-29']},
            {'ageGroup': '30-39', 'percentage': age_percentage['30-39']},
            {'ageGroup': '40-59', 'percentage': age_percentage['40-59']},
            {'ageGroup': '60+', 'percentage': age_percentage['Over 60']},
        ],
    }

    return JsonResponse(statistics, safe=False)

def number_of_respondents(country):
    communities = Community.objects.filter(countryid=country)
    respondents = 0
    for community in communities:
        respondents += Person.objects.filter(communityid=community.communityid).count()        
    return respondents

def get_country(request):
    countryList = []

    # Get all country IDs that exist in the Community table
    country_ids = Community.objects.values_list('countryid', flat=True).distinct()
    # Use those IDs to filter Country instances
    countries = Country.objects.filter(countryid__in=country_ids)

    for country in countries:        
        countryInfo = {
            'code': country.code,
            'country': country.name,
            'latitude': country.latitude, 
            'longitude': country.longitude, 
            'regionNumber': country.countryid, 
            'respondants': number_of_respondents(country),
        }
        countryList.append(countryInfo)

    return JsonResponse(countryList, safe=False)

def get_country_response(request, countrycode):
    country = Country.objects.get(code=countrycode)
    number_of_regions = Community.objects.filter(countryid=country.countryid).distinct().count()
    community_ids = Community.objects.filter(countryid=country.countryid).values_list('communityid', flat=True)
    people = Person.objects.filter(communityid__in=community_ids)
    respondents = number_of_respondents(country)
    age_percentage = age_range_percentages(respondents, people)
    most_recent_response = Response.objects.filter(personid__in=people).order_by('-responsetimestamp').first()

    # Extract the timestamp if a response exists, else default to None or a suitable placeholder.
    last_response_date = most_recent_response.responsetimestamp if most_recent_response else 'No responses'

    gender_count = count_persons_by_gender(people)

    countryRegions = []
    for communityid in community_ids:
        community = Community.objects.get(communityid=communityid)
        person_ids = Person.objects.filter(communityid=communityid).values_list('personid', flat=True)
        community_info = {
            'id': communityid,
            'region': community.city,
            'responses': Response.objects.filter(personid__in=person_ids).count()
        }
        countryRegions.append(community_info)

    countryResponse = {
        'countryInfo': {
            'code': countrycode,
            'countryName': country.name,
            'respondents': respondents,
            'regions': number_of_regions,
            'lastResponseDate': last_response_date.strftime("%B %d, %Y") if most_recent_response else last_response_date,
            'genderRatio': {
                'male': gender_count['Male'],
                'female': gender_count['Female'],
            },
            'ageDistribution': [
                {'ageGroup': '0-14', 'percentage': age_percentage['0-14']},
                {'ageGroup': '15-21', 'percentage': age_percentage['15-21']},
                {'ageGroup': '22-29', 'percentage': age_percentage['22-29']},
                {'ageGroup': '30-39', 'percentage': age_percentage['30-39']},
                {'ageGroup': '40-59', 'percentage': age_percentage['40-59']},
                {'ageGroup': '60+', 'percentage': age_percentage['Over 60']},
            ],
        },
        'countryRegions': countryRegions,
    }

    return JsonResponse(countryResponse, safe=False)