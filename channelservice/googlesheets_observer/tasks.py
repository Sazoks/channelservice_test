from celery import shared_task


@shared_task
def t():
    print('hello')
    return 'hello'
