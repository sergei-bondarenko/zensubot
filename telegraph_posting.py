from telegraph import Telegraph

class TelegraphPost:
    telegraph = Telegraph()

    @classmethod
    def post_to_telegraph(cls, text):
        response = cls.telegraph.create_page(
            f'5 days',
            html_content=text,
            author_name = '@zensu', 
            author_url='https://t.me/zensu'
        )

        return 'https://telegra.ph/{}'.format(response['path'])
    
    @classmethod
    def login(cls):
        cls.telegraph.create_account(short_name='zensu')