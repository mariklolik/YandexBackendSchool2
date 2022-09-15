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


def item_in_actual(id: str):
    session = create_session()
    item = session.query(ItemActual).filter(ItemActual.id == id).first()
    return item is not None


def update(id: str, new_data: dict, update_date):
    session = create_session()
    actual_item = session.query(ItemActual).filter(ItemActual.id == id).first()  # Fetching actual item
    actual_item_json = copy(actual_item.__dict__)
    del actual_item_json['_sa_instance_state']
    del actual_item_json['numericid']  # Auto-increment
    old_item = ItemOld(**actual_item_json)  # Making a copy with another class
    session.add(old_item)  # Push to old
    session.delete(actual_item)  # Item not in actual table any more
    new_data['date'] = update_date
    new_item = ItemActual(**new_data)
    session.add(new_item)  # To actual table
    session.commit()


def get_subtree(id, session=None):
    if session is None:
        session = create_session()
    item = session.query(ItemActual).filter(ItemActual.id == id).first()
    if item.type == "FILE":
        return item
    leaves = session.query(ItemActual).filter(ItemActual.parentId == id)
    result = []
    for i in leaves:
        result.append(get_subtree(i.id, session))
    return [item, *result]


def get_parents(id):
    session = create_session()
    item = session.query(ItemActual).filter(ItemActual.id == id).first()
    item_parent = session.query(ItemActual).filter(ItemActual.id == item.parentId).first()
    parents = []
    while item_parent is not None:
        parents.append(copy(item_parent))
        item_parent = session.query(ItemActual).filter(ItemActual.id == item_parent.parentId).first()
    return parents


def get_size(item_id):
    session = create_session()
    item = session.query(ItemActual).filter(ItemActual.id == item_id).first()
    if item is None:
        return 0
    size = 0
    children_counter = 0
    item_leaves = get_subtree(item.id)
    if type(item_leaves) != list:
        return item_leaves.size, 1
    for SubObject in item_leaves:
        if type(SubObject) == list:  # SubObject is also a tree
            size, children_counter = size + get_size(SubObject[0].id)[0], children_counter + \
                                     get_size(SubObject[0].id)[1]  # 0 element of subtree is the father-node
        else:
            if SubObject.type == "FILE":
                size += SubObject.size
                children_counter += 1
    return size, children_counter


def update_leaves_date(leaves, new_date):
    for i in leaves:
        if type(i) == list:
            update_leaves_date(i, new_date)
        else:
            i_json = copy(i.__dict__)
            del i_json['_sa_instance_state']
            i_json['date'] = new_date
            update(i.id, i_json, new_date)


def add_to_database(data: dict):
    session = create_session()
    new_item = ItemActual(**data)
    session.add(new_item)
    session.commit()


def check(item):
    if item['id'] is None:
        return False
    if item["id"] == "null":
        return False
    if item["type"] == "FOLDER" and "url" in item.keys() and item["url"] != "null":
        return False
    if item["type"] == "FILE" and len(item["url"]) > 255:
        return False
    if item["type"] == "FOLDER" and "size" in item.keys() and item["size"] != "null":
        return False
    if item["type"] == "FILE" and int(item["size"]) <= 0:
        return False
    return True


@blueprint.route("/imports", methods=["POST", "GET"])
def imports_function():
    fetched_data = request.json

    update_date = fetched_data['updateDate']
    if not datetime_valid(update_date):
        return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400

    update_date = datetime.fromisoformat(update_date.replace("Z", "+00:00"))

    for item in fetched_data['items']:
        if not check(item):
            return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
        if item_in_actual(item['id']):
            update(item['id'], item, update_date)

            leaves = [get_subtree(item['id'])]
            update_leaves_date(leaves, update_date)

            parents = get_parents(item['id'])
            for i in parents:
                parent_data = i.__dict__
                del parent_data['_sa_instance_state']
                full_size, offer_counter = get_size(i.id)
                if offer_counter != 0:
                    new_parent_size = full_size
                else:
                    new_parent_size = 0
                parent_data['size'] = new_parent_size
                update(i.id, parent_data, update_date)
        else:
            item['date'] = update_date
            add_to_database(item)
            full_size, offer_counter = get_size(item['id'])
            if offer_counter != 0:
                item['size'] = full_size
            else:
                item['size'] = 0
            update(item['id'], item, update_date)
            parents = get_parents(item['id'])
            for i in parents:
                parent_data = copy(i.__dict__)
                del parent_data['_sa_instance_state']
                full_size, offer_counter = get_size(parent_data['id'])
                if offer_counter != 0:
                    new_parent_size = full_size
                else:
                    new_parent_size = 0
                parent_data['size'] = new_parent_size
                update(i.id, parent_data, update_date)

    return Response(status=200)


def delete_subtree(leaves, session):
    for i in leaves:
        if type(i) == list:
            delete_subtree(i, session)
        else:
            old_copies = session.query(ItemOld).filter(ItemOld.id == i.id).all()
            for old in old_copies:
                session.delete(old)
            session.delete(i)


def form_dict(leaves):
    if type(leaves) == ItemActual:
        leaves = [leaves]
    result = copy(leaves[0].__dict__)

    del result['_sa_instance_state']
    del result['numericid']
    if result['size'] == 0 and result['type'] == 'FOLDER':
        result['size'] = 0
    result['date'] = result['date'].strftime("%Y-%m-%dT%H:%M:%SZ")
    result['children'] = []
    for i in range(1, len(leaves)):
        if type(leaves[i]) == list:
            subtree_json = form_dict(leaves[i])
            result['children'].append(subtree_json)
        else:
            subtree_json = copy(leaves[i].__dict__)
            del subtree_json['numericid']
            del subtree_json['_sa_instance_state']
            subtree_json['date'] = subtree_json['date'].strftime("%Y-%m-%dT%H:%M:%SZ")
            subtree_json['children'] = None
            result['children'].append(subtree_json)
    if 'children' in result.keys():
        if result['children'] == [] and result['type'] == 'FILE':
            result['children'] = None
    return result


@blueprint.route("/delete/<string:id>", methods=["DELETE", "GET"])
def delete_item(id: str):
    session = create_session()

    item = session.query(ItemActual).filter(ItemActual.id == id).first()

    if item is None:
        return json.loads("{\n  \"code\": 404,\n  \"message\": \"Item not found\"\n}"), 404

    parents = get_parents(item.id)
    leaves = [get_subtree(id, session)]
    delete_subtree(leaves, session)
    session.commit()
    for i in parents:
        parent_data = i.__dict__
        del parent_data['_sa_instance_state']
        full_size, offer_counter = get_size(i.id)
        if offer_counter != 0:
            new_parent_size = full_size
        else:
            new_parent_size = 0
        parent_data['size'] = new_parent_size
        update(i.id, parent_data, parent_data['date'])

    session.commit()
    return Response(status=200)


@blueprint.route("/nodes/<string:id>", methods=["GET", "POST"])
def info(id: str):
    session = create_session()
    # if len(id) != 36:
    #     return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
    item = session.query(ItemActual).filter(ItemActual.id == id).first()
    if item is None:
        return json.loads("{\n  \"code\": 404,\n  \"message\": \"Item not found\"\n}"), 404
    print(item)
    ans = form_dict(get_subtree(id, session))
    return json.dumps(ans)


@blueprint.route("/updates", methods=["GET", "POST"])
def sales():
    session = create_session()
    content = request.args
    date = content.get('date')
    if not datetime_valid(date):
        return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
    date = datetime.fromisoformat(date.replace("Z", "+00:00"))

    items = session.query(ItemActual).filter(ItemActual.type == "FILE", ItemActual.date <= date,
                                             ItemActual.date >= date - timedelta(days=1)).all()
    ans = {'items': []}
    for item in items:
        item_json = copy(item.__dict__)
        del item_json['numericid']
        del item_json['_sa_instance_state']
        item_json['date'] = item_json['date'].strftime("%Y-%m-%dT%H:%M:%SZ")
        item_json['children'] = None
        ans['items'].append(item_json)
    if not ans['items']:
        ans['items'] = None
    session.close()
    return json.dumps(ans)


def get_last_state(id, timestamp, session):
    old_items = session.query(ItemOld).filter(ItemOld.id == id, ItemOld.date == timestamp)
    max_olditem = max(old_items, key=lambda x: x.numericid)

    new_item = session.query(ItemActual).filter(ItemActual.id == id, ItemActual.date == timestamp).first()
    if new_item is not None:
        item = new_item
    else:
        item = max_olditem
    return item


def get_subtree_state(id, timestamp, session):
    if session is None:
        session = create_session()
    item = get_last_state(id, timestamp, session)
    if item.type == "FILE":
        return item

    leaves_new = session.query(ItemActual).filter(ItemActual.parentId == id,
                                                  ItemActual.date <= timestamp).all()
    leaves_new_names = [i.url for i in leaves_new]
    leaves_old = session.query(ItemOld).filter(ItemOld.parentId, ItemOld.date <= timestamp).all()
    leaves = [*leaves_new]
    for i in leaves_old:
        same = [j for j in leaves_old if j.url == i.url]
        max_leave = max(same, key=lambda x: x.numericid)
        if max_leave.url not in leaves_new_names:
            leaves.append(max_leave)
    leaves = list(set(leaves))

    result = []
    for i in leaves:
        result.append(get_subtree(i.id, session))
    return [item, *result]


@blueprint.route("/node/<string:id>/history", methods=["GET", "POST"])
def stats(id):
    session = create_session()
    content = request.args

    date_start = content.get('dateStart')
    if not datetime_valid(date_start):
        return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
    date_start = datetime.fromisoformat(date_start.replace("Z", "+00:00"))

    date_end = content.get('dateEnd')
    if not datetime_valid(date_end):
        print("not valid time")
        return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
    date_end = datetime.fromisoformat(date_end.replace("Z", "+00:00"))

    new_item = session.query(ItemActual).filter(ItemActual.id == id).first()
    if new_item is None:
        return json.loads("{\n  \"code\": 404,\n  \"message\": \"Item not found\"\n}"), 404

    timestamps = list(
        set([i.date for i in session.query(ItemOld).filter(ItemOld.id == id, ItemOld.date >= date_start,
                                                           ItemOld.date < date_end).all()]))
    result = {'items': []}
    # print(date_start, timestamps, date_end)
    for time in timestamps:
        item = get_last_state(id, time, session)
        result['items'].append(form_dict(get_subtree_state(item.id, time, session)))
    return json.dumps(result)
