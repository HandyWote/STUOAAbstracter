from flask import Flask, request, jsonify
import sqlite3 as sqlite
from datetime import datetime, timedelta
from peewee import SqliteDatabase, Model, CharField, DateTimeField

# 配置数据库连接
db = SqliteDatabase('user.db', pragmas={
    'journal_mode': 'wal',
    'foreign_keys': 1,
    'ignore_check_constraints': 0
})

# 定义用户模型
class User(Model):
    email = CharField(unique=True)
    created_at = DateTimeField(default=datetime.now)
    subscription_end = DateTimeField()
    
    class Meta:
        database = db

# 初始化数据库
def init_db():
    db.connect()
    db.create_tables([User])

def addUser(email):
    """添加订阅记录"""
    try:
        User.create(
            email=email,
            subscription_end=datetime.now() + timedelta(days=365)
        )
        print(f"成功添加订阅：{email}")
        return True
    except Exception as e:
        print(f"邮箱 {email} 已存在，更新订阅时间")
        user = User.get(User.email == email)
        user.subscription_end = datetime.now() + timedelta(days=365)
        user.save()
        return False

# 查询所有订阅
def getAllUsers():
    """获取所有订阅信息"""
    return [user.email for user in User.select().order_by(User.id)]

#删除订阅
def deleteUser(email):
    """根据邮箱删除订阅记录"""
    try:
        user = User.get(User.email == email)
        user.delete_instance()
        print(f"成功删除订阅：{email}")
        return True
    except User.DoesNotExist:
        print(f"邮箱 {email} 不存在")
        return False
    except Exception as e:
        print(f"删除订阅失败：{e}")
        return False

def getLimitedUsers(days=7):
    """获取即将过期的订阅"""
    end_date = datetime.now() + timedelta(days=days)
    return [user.email for user in User.select().where(
        (User.subscription_end >= datetime.now()) &
        (User.subscription_end <= end_date)
    )]

app = Flask(__name__)

@app.route("/api/subscribe", methods=['POST'])
def subscribe():
    email = request.json.get("email")
    print(email)
    try:
        addUser(email)
        return jsonify({
            'success': True,
            'message': '订阅成功',
            'data': {
                'email': email,
                'payment_url': 'https://payment.example.com/checkout'
            }
        })
    except Exception as e:
        print(f'订阅失败: {e}')
        return jsonify({'success': False, 'message': '订阅失败，请重试'})



if __name__ == '__main__':
    init_db()
    app.run()