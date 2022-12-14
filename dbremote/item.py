import sqlalchemy

import uuid
from .db_session import SqlAlchemyBase


class ItemActual(SqlAlchemyBase):
    __tablename__ = 'actual'
    numericid = sqlalchemy.Column('numericid', sqlalchemy.Integer, primary_key=True, autoincrement=True)
    id = sqlalchemy.Column('id', sqlalchemy.Text(length=36), default=lambda: str(uuid.uuid4()), primary_key=False)
    parentId = sqlalchemy.Column('parentId', sqlalchemy.Text(length=36), default=None,
                                 primary_key=False)

    url = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    size = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, default=0)
    date = sqlalchemy.Column(sqlalchemy.DateTime)
    type = sqlalchemy.Column(sqlalchemy.String, nullable=False)


class ItemOld(SqlAlchemyBase):
    __tablename__ = 'old'
    numericid = sqlalchemy.Column('numericid', sqlalchemy.Integer, primary_key=True, autoincrement=True)
    id = sqlalchemy.Column('id', sqlalchemy.Text(length=36), default=lambda: str(uuid.uuid4()), primary_key=False)
    parentId = sqlalchemy.Column('parentId', sqlalchemy.Text(length=36), default=None,
                                 primary_key=False)

    url = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    size = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, default=0)
    date = sqlalchemy.Column(sqlalchemy.DateTime)
    type = sqlalchemy.Column(sqlalchemy.String, nullable=False)
