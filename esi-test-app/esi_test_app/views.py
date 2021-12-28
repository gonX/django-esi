import logging

from django.shortcuts import render, redirect

from esi.clients import EsiClientProvider
from esi.models import Token
from esi.decorators import token_required, single_use_token

from esi import __version__

# create client provider
esi = EsiClientProvider(app_info_text=f"esi-test-app {__version__}")

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
    return render(
        request,
        'esi_test_app/index.html', context={'scopes': ESI_SCOPES}
    )


@single_use_token(scopes=ESI_SCOPES)
def test_single_use_token(request, token):
    request.session['token_pk'] = token.pk
    request.session['test_name'] = 'test 1 - single_use_token'
    return redirect('esi_test_app:run_api_test')


def test_token_required_1(request):
    """Preparing environment for test"""
    logger.info('--------------------------------------------')
    logger.info(f'starting API test with user {request.user.username}')
    Token.objects.filter(user=request.user, scopes__name__in=ESI_SCOPES).delete()
    return redirect('esi_test_app:test_token_required_2')


@token_required(scopes=ESI_SCOPES)
def test_token_required_2(request, token):
    request.session['token_pk'] = token.pk
    request.session['test_name'] = 'test 2 - token_required'
    return redirect('esi_test_app:run_api_test')


def run_api_test(request):
    """Running the API test"""
    logger.info('starting ESI client')
    token = Token.objects.get(pk=request.session['token_pk'])

    try:
        logger.info('making call to ESI with token')
        esi.client.Character\
            .get_characters_character_id_medals(
                character_id=token.character_id,
                token=token.valid_access_token()
            )\
            .result()
        test_success = True
        error_str = None
        logger.info('API test succeeded')

    except Exception as ex:
        test_success = False
        logger.exception(f'API test failed: {ex}')
        error_str = str(ex)

    context = {
        'test_name': request.session['test_name'],
        'test_success': test_success,
        'error_str': error_str,
        'esi_endpoint': '/characters/{character_id}/medals/'
    }
    return render(request, 'esi_test_app/test_result.html', context)
