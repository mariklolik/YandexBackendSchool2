from dbremote.db_session import create_session, global_init
from flask import request, Blueprint, Response
from dbremote.item import ItemOld, ItemActual
from datetime import datetime, timedelta
import json
from copy import copy

global_init("db/data.sqlite")
blueprint = Blueprint('api', __name__)


@blueprint.errorhandler(400)
def val_failed_error():
    return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400


@blueprint.errorhandler(404)
def not_found_error():
    return json.loads("{\n  \"code\": 404,\n  \"message\": \"Item not found\"\n}"), 404


def datetime_valid(dt_str):
    try:
        datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except:
        return False
    return True


def ItemInActual(id: str):
    session = create_session()
    Item = session.query(ItemActual).filter(ItemActual.id == id).first()
    return Item != None


def update(id: str, NewData: dict, UpdateDate):
    session = create_session()
    ActualItem = session.query(ItemActual).filter(ItemActual.id == id).first()  # Fetching actual item
    ActualItemJSON = copy(ActualItem.__dict__)
    del ActualItemJSON['_sa_instance_state']
    del ActualItemJSON['numericid']  # Auto-increment
    OldItem = ItemOld(**ActualItemJSON)  # Making a copy with another class
    session.add(OldItem)  # Push to old
    session.delete(ActualItem)  # Item not in actual table any more
    NewData['date'] = UpdateDate
    NewItem = ItemActual(**NewData)
    session.add(NewItem)  # To actual table
    session.commit()


def GetSubtree(id, session=None):
    if (session == None):
        session = create_session()
    Item = session.query(ItemActual).filter(ItemActual.id == id).first()
    if Item.type == "FILE":
        return Item
    Leaves = session.query(ItemActual).filter(ItemActual.parentId == id)
    result = []
    for i in Leaves:
        result.append(GetSubtree(i.id, session))
    return [Item, *result]


def GetParents(id):
    session = create_session()
    Item = session.query(ItemActual).filter(ItemActual.id == id).first()
    ItemParent = session.query(ItemActual).filter(ItemActual.id == Item.parentId).first()
    parents = []
    while (ItemParent != None):
        parents.append(copy(ItemParent))
        ItemParent = session.query(ItemActual).filter(ItemActual.id == ItemParent.parentId).first()
    return parents


def GetSize(ItemId):
    session = create_session()
    ItemItem = session.query(ItemActual).filter(ItemActual.id == ItemId).first()
    if ItemItem == None:
        return 0
    size = 0
    children_counter = 0
    ItemLeaves = GetSubtree(ItemItem.id)
    if type(ItemLeaves) != list:
        return ItemLeaves.size, 1
    for SubObject in ItemLeaves:
        if type(SubObject) == list:  # SubObject is also a tree
            size, children_counter = size + GetSize(SubObject[0].id)[0], children_counter + \
                                     GetSize(SubObject[0].id)[1]  # 0 element of subtree is the father-node
        else:
            if (SubObject.type == "FILE"):
                size += SubObject.size
                children_counter += 1
    return size, children_counter


def UpdateLeavesDate(Leaves, NewDate):
    for i in Leaves:
        if type(i) == list:
            UpdateLeavesDate(i, NewDate)
        else:
            Ijson = copy(i.__dict__)
            del Ijson['_sa_instance_state']
            Ijson['date'] = NewDate
            update(i.id, Ijson, NewDate)


def AddToDataBase(Data: dict):
    session = create_session()
    NewItem = ItemActual(**Data)
    session.add(NewItem)
    session.commit()


@blueprint.route("/imports", methods=["POST", "GET"])
def imports_function():
    FetchedData = request.json

    UpdateDate = FetchedData['updateDate']
    if not datetime_valid(UpdateDate):
        return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400

    UpdateDate = datetime.fromisoformat(UpdateDate.replace("Z", "+00:00"))

    for item in FetchedData['items']:
        if ItemInActual(item['id']):
            update(item['id'], item, UpdateDate)

            Leaves = [GetSubtree(item['id'])]
            UpdateLeavesDate(Leaves, UpdateDate)

            Parents = GetParents(item['id'])
            for i in Parents:
                ParentData = i.__dict__
                del ParentData['_sa_instance_state']
                FullSize, Offercounter = GetSize(i.id)
                if Offercounter != 0:
                    NewParentSize = (FullSize)
                else:
                    NewParentSize = 0
                ParentData['size'] = NewParentSize
                update(i.id, ParentData, UpdateDate)
        else:
            item['date'] = UpdateDate
            AddToDataBase(item)
            FullSize, Offercounter = GetSize(item['id'])
            if Offercounter != 0:
                item['size'] = (FullSize)
            else:
                item['size'] = 0
            update(item['id'], item, UpdateDate)
            Parents = GetParents(item['id'])
            for i in Parents:
                ParentData = copy(i.__dict__)
                del ParentData['_sa_instance_state']
                FullSize, Offercounter = GetSize(ParentData['id'])
                if Offercounter != 0:
                    NewParentSize = (FullSize)
                else:
                    NewParentSize = 0
                ParentData['size'] = NewParentSize
                update(i.id, ParentData, UpdateDate)

    return Response(status=200)


def DeleteSubtree(Leaves, session):
    for i in Leaves:
        if type(i) == list:
            DeleteSubtree(i, session)
        else:
            OldCopies = session.query(ItemOld).filter(ItemOld.id == i.id).all()
            for old in OldCopies:
                session.delete(old)
            session.delete(i)


def FormDict(Leaves):
    result = copy(Leaves[0].__dict__)
    del result['_sa_instance_state']
    del result['numericid']
    if result['size'] == 0 and result['type'] == 'FOLDER':
        result['size'] = None
    result['date'] = result['date'].strftime("%Y-%m-%dT%H:%M:%SZ")
    result['children'] = []
    for i in range(1, len(Leaves)):
        if type(Leaves[i]) == list:
            SubTreeJSON = FormDict(Leaves[i])
            result['children'].append(SubTreeJSON)
        else:
            SubTreeJSON = copy(Leaves[i].__dict__)
            del SubTreeJSON['numericid']
            del SubTreeJSON['_sa_instance_state']
            SubTreeJSON['date'] = SubTreeJSON['date'].strftime("%Y-%m-%dT%H:%M:%SZ")
            SubTreeJSON['children'] = None
            result['children'].append(SubTreeJSON)

    return result


@blueprint.route("/delete/<string:id>", methods=["DELETE", "GET"])
def delete_item(id: str):
    session = create_session()

    Item = session.query(ItemActual).filter(ItemActual.id == id).first()

    if Item == None:
        return json.loads("{\n  \"code\": 404,\n  \"message\": \"Item not found\"\n}"), 404

    Parents = GetParents(Item.id)
    Leaves = [GetSubtree(id, session)]
    DeleteSubtree(Leaves, session)
    session.commit()
    for i in Parents:
        ParentData = i.__dict__
        del ParentData['_sa_instance_state']
        FullSize, Offercounter = GetSize(i.id)
        if Offercounter != 0:
            NewParentSize = (FullSize)
        else:
            NewParentSize = 0
        ParentData['size'] = NewParentSize
        update(i.id, ParentData, ParentData['date'])

    session.commit()
    return Response(status=200)


@blueprint.route("/nodes/<string:id>", methods=["GET", "POST"])
def info(id: str):
    session = create_session()
    if len(id) != 36:
        return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
    Item = session.query(ItemActual).filter(ItemActual.id == id).first()
    if Item == None:
        return json.loads("{\n  \"code\": 404,\n  \"message\": \"Item not found\"\n}"), 404
    Ans = FormDict(GetSubtree(id, session))
    return json.dumps(Ans)


@blueprint.route("/updates", methods=["GET", "POST"])
def sales():
    session = create_session()
    content = request.args
    date = content.get('date')
    if not datetime_valid(date):
        return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
    date = datetime.fromisoformat(date.replace("Z", "+00:00"))

    Items = session.query(ItemActual).filter(ItemActual.type == "FILE", ItemActual.date <= date,
                                                 ItemActual.date >= date - timedelta(days=1)).all()
    Ans = {'items': []}
    for item in Items:
        ItemJSON = copy(item.__dict__)
        del ItemJSON['numericid']
        del ItemJSON['_sa_instance_state']
        ItemJSON['date'] = ItemJSON['date'].strftime("%Y-%m-%dT%H:%M:%SZ")
        ItemJSON['children'] = None
        Ans['items'].append(ItemJSON)
    if Ans['items'] == []:
        Ans['items'] = None
    session.close()
    return json.dumps(Ans)


def GetLastState(id, timestamp, session):
    AllOldItems = session.query(ItemOld).filter(ItemOld.id == id, ItemOld.date == timestamp)
    MaxOldItem = max(AllOldItems, key=lambda x: x.numericid)

    NewItem = session.query(ItemActual).filter(ItemActual.id == id, ItemActual.date == timestamp).first()
    if NewItem != None:
        Item = NewItem
    else:
        Item = MaxOldItem
    return Item


def GetSubtreeState(id, timestamp, session):
    if (session == None):
        session = create_session()
    Item = GetLastState(id, timestamp, session)
    if Item.type == "FILE":
        return Item

    LeavesNew = session.query(ItemActual).filter(ItemActual.parentId == id,
                                                     ItemActual.date <= timestamp).all()
    LeavesNewNames = [i.url for i in LeavesNew]
    LeavesOld = session.query(ItemOld).filter(ItemOld.parentId, ItemOld.date <= timestamp).all()
    Leaves = [*LeavesNew]
    for i in LeavesOld:
        Same = [j for j in LeavesOld if j.url == i.url]
        MaxLeave = max(Same, key=lambda x: x.numericid)
        if MaxLeave.url not in LeavesNewNames:
            Leaves.append(MaxLeave)
    Leaves = list(set(Leaves))

    result = []
    for i in Leaves:
        result.append(GetSubtree(i.id, session))
    return [Item, *result]


@blueprint.route("/node/<string:id>/history", methods=["GET", "POST"])
def stats(id):
    session = create_session()
    content = request.args

    DateStart = content.get('dateStart')
    if not datetime_valid(DateStart):
        return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
    DateStart = datetime.fromisoformat(DateStart.replace("Z", "+00:00"))

    DateEnd = content.get('dateEnd')
    if not datetime_valid(DateEnd):
        print("not valid time")
        return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
    DateEnd = datetime.fromisoformat(DateEnd.replace("Z", "+00:00"))

    NewItem = session.query(ItemActual).filter(ItemActual.id == id).first()
    if NewItem is None:
        return json.loads("{\n  \"code\": 404,\n  \"message\": \"Item not found\"\n}"), 404

    Timestamps = list(
        set([i.date for i in session.query(ItemOld).filter(ItemOld.id == id, ItemOld.date >= DateStart,
                                                               ItemOld.date < DateEnd).all()]))
    Result = {'items': []}
    # print(DateStart, Timestamps, DateEnd)
    for time in Timestamps:
        Item = GetLastState(id, time, session)
        Result['items'].append(FormDict(GetSubtreeState(Item.id, time, session)))
    return json.dumps(Result)
