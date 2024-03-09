import sqlalchemy as sq
from sqlalchemy.orm import sessionmaker
from Class import initialize_database, CustomWord

def populate_db(engine):
    words = (
        ('Hello', 'Привет'),
        ('Dog', 'Собака'),
        ('Window', 'Окно'),
        ('Bed', 'Кровать'),
        ('Cup', 'Чашка'),
        ('Watch', 'Часы'),
        ('Paper', 'Бумага'),
        ('Scales', 'Весы'),
        ('Table', 'Стол'),
        ('Chair', 'Стул')
    )
    initialize_database(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    for word_pair in words:
        session.add(CustomWord(custom_word=word_pair[0], custom_translate=word_pair[1]))
    session.commit()
    session.close()

db_engine = sq.create_engine('postgresql://postgres:password@localhost:5432/tgbot')
populate_db(db_engine)