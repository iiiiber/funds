"""API响应封装"""
from flask import jsonify

def success(data=None, message='操作成功'):
    """成功响应"""
    result = {'success': True, 'message': message}
    if data is not None:
        result['data'] = data
    return jsonify(result)

def error(message='操作失败', code=400):
    """错误响应"""
    return jsonify({'success': False, 'message': message}), code

def page_data(items, total, page, page_size):
    """分页数据"""
    return {
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if page_size > 0 else 0
    }
