import logging

from django.shortcuts import render, redirect
from django.http import HttpResponse

from esi.clients import esi_client_factory
from esi.models import Token
from esi.decorators import token_required


# setup logger
logger = logging.getLogger(__name__)
f_handler = logging.FileHandler('esi_test_api.log')
f_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
f_handler.setFormatter(f_format)
logger.addHandler(f_handler)
logger.setLevel(logging.DEBUG)


ESI_SCOPES = ['esi-characters.read_medals.v1']


def index(request):        
    """Start page with ability to login"""
    if request.method == 'POST':        
        return redirect('esi_test_app:prepare_api_test')    
    else:                
        return render(
            request, 
            'esi_test_app/index.html', context={'scopes': ESI_SCOPES}
        )


def prepare_api_test(request):
    """Preparing environment for test"""
    logger.info('--------------------------------------------')
    logger.info('starting API test with user {}'.format(request.user.username))    
    Token.objects.filter(user=request.user, scopes__name__in=ESI_SCOPES).delete()
    return redirect('esi_test_app:run_api_test')


@token_required(scopes=ESI_SCOPES)
def run_api_test(request, token):        
    """Running the API test"""
    logger.info('starting ESI client')
    client = esi_client_factory(token=token)

    try:
        logger.info('making call to ESI with token')
        client.Character\
            .get_characters_character_id_medals(character_id=token.character_id)\
            .result()
        test_success = True
        error_str = None
        logger.info('API test succeeded')
    except Exception as ex:
        test_success = False        
        logger.exception('API test failed: {}'.format(ex))
        error_str = str(ex)

    context = {
        'test_success': test_success,
        'error_str': error_str,
        'esi_endpoint': '/characters/{character_id}/medals/'
    }

    return render(request, 'esi_test_app/test_result.html', context)
