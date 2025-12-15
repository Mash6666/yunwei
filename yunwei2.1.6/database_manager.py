#!/usr/bin/env python3
"""
数据库管理器 - MySQL数据库连接和操作
"""
import pymysql
from typing import List, Dict, Any, Optional
import json
from dataclasses import dataclass
from logger_config import get_logger
from config import Config

logger = get_logger(__name__)

@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = "123456"
    database: Optional[str] = None
    charset: str = "utf8mb4"

    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """从环境变量创建配置"""
        db_config = Config.get_database_config()
        return cls(
            host=db_config["host"],
            port=db_config["port"],
            user=db_config["user"],
            password=db_config["password"],
            charset=db_config["charset"]
        )

class DatabaseManager:
    """数据库管理器"""

    def __init__(self, config: DatabaseConfig = None):
        self.config = config or DatabaseConfig.from_env()
        self.connection = None
        logger.info(f"数据库管理器初始化完成 - 主机: {self.config.host}:{self.config.port}, 用户: {self.config.user}")

        # 记录配置信息（隐藏密码）
        safe_config = self.config.__dict__.copy()
        if 'password' in safe_config:
            safe_config['password'] = '***'
        logger.debug(f"数据库配置: {safe_config}")

    def connect(self, database: str = None) -> bool:
        """连接数据库"""
        start_time = logger.info(f"开始连接数据库 - 主机: {self.config.host}:{self.config.port}, 数据库: {database or '未指定'}")

        try:
            if database:
                self.config.database = database
                logger.debug(f"设置目标数据库: {database}")

            self.connection = pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                charset=self.config.charset,
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10,
                read_timeout=30,
                write_timeout=30
            )

            connection_info = f"{self.config.host}:{self.config.port}"
            if database:
                connection_info += f"/{database}"

            logger.info(f"✅ 成功连接到MySQL数据库: {connection_info}")
            return True

        except Exception as e:
            logger.error(f"❌ 连接数据库失败 - {self.config.host}:{self.config.port} - 错误: {str(e)}")
            logger.debug(f"数据库连接详情 - 用户: {self.config.user}, 字符集: {self.config.charset}")
            return False

    def disconnect(self):
        """断开数据库连接"""
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
                logger.info("✅ 数据库连接已关闭")
            except Exception as e:
                logger.warning(f"关闭数据库连接时出现警告: {e}")
        else:
            logger.debug("数据库连接已处于断开状态")

    def get_databases(self) -> List[str]:
        """获取所有数据库列表"""
        logger.debug("开始获取数据库列表")

        try:
            if not self.connection:
                logger.debug("数据库未连接，尝试连接")
                if not self.connect():
                    logger.error("无法连接到数据库，获取数据库列表失败")
                    return []

            cursor = self.connection.cursor()
            logger.debug("执行 SHOW DATABASES 查询")
            cursor.execute("SHOW DATABASES")
            databases = [row['Database'] for row in cursor.fetchall()]
            cursor.close()

            # 过滤掉系统数据库
            system_prefixes = ['information_', 'performance_', 'mysql_', 'sys']
            filtered_databases = [db for db in databases
                                 if not any(db.startswith(prefix) for prefix in system_prefixes)]

            logger.info(f"✅ 获取到 {len(filtered_databases)} 个用户数据库")
            logger.debug(f"数据库列表: {filtered_databases}")
            return filtered_databases

        except Exception as e:
            logger.error(f"❌ 获取数据库列表失败: {e}")
            logger.debug(f"错误详情 - 连接状态: {self.connection is not None}")
            return []

    def get_tables(self, database: str) -> List[str]:
        """获取指定数据库的所有表"""
        try:
            if not self.connect(database):
                return []

            cursor = self.connection.cursor()
            cursor.execute("SHOW TABLES")
            # 对于SHOW TABLES，结果中通常只有一个字段，字段名可能是动态的
            tables = [list(row.values())[0] for row in cursor.fetchall()]
            cursor.close()

            logger.info(f"数据库 {database} 中有 {len(tables)} 个表")
            return tables

        except Exception as e:
            logger.error(f"获取表列表失败: {e}")
            return []

    def get_table_structure(self, database: str, table: str) -> List[Dict[str, Any]]:
        """获取表结构"""
        try:
            if not self.connect(database):
                return []

            cursor = self.connection.cursor()
            cursor.execute(f"DESCRIBE `{table}`")
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    'field': row['Field'],
                    'type': row['Type'],
                    'null': row['Null'],
                    'key': row['Key'],
                    'default': row['Default'],
                    'extra': row['Extra']
                })
            cursor.close()

            logger.info(f"表 {table} 有 {len(columns)} 个字段")
            return columns

        except Exception as e:
            logger.error(f"获取表结构失败: {e}")
            return []

    def get_table_data(self, database: str, table: str, limit: int = 100) -> Dict[str, Any]:
        """获取表数据"""
        try:
            if not self.connect(database):
                return {'success': False, 'error': '数据库连接失败'}

            cursor = self.connection.cursor()

            # 获取总记录数
            cursor.execute(f"SELECT COUNT(*) as total FROM `{table}`")
            total_count = cursor.fetchone()['total']

            # 获取表数据
            cursor.execute(f"SELECT * FROM `{table}` LIMIT {limit}")
            data = cursor.fetchall()

            # 转换datetime对象为字符串
            for row in data:
                for key, value in row.items():
                    if hasattr(value, 'strftime'):
                        row[key] = value.strftime('%Y-%m-%d %H:%M:%S')

            cursor.close()

            result = {
                'success': True,
                'total_count': total_count,
                'limit': limit,
                'data': data,
                'columns': list(data[0].keys()) if data else []
            }

            logger.info(f"表 {table} 获取到 {len(data)} 条记录 (总共 {total_count} 条)")
            return result

        except Exception as e:
            logger.error(f"获取表数据失败: {e}")
            return {'success': False, 'error': str(e)}

    def execute_query(self, database: str, query: str) -> Dict[str, Any]:
        """执行SQL查询"""
        logger.debug(f"开始执行SQL查询 - 数据库: {database}")
        logger.debug(f"SQL语句: {query}")

        try:
            if not self.connect(database):
                error_msg = f"无法连接到数据库 {database}"
                logger.error(f"❌ {error_msg}")
                return {'success': False, 'error': error_msg}

            cursor = self.connection.cursor()

            # 安全检查：只允许SELECT查询
            query_upper = query.strip().upper()
            if not query_upper.startswith('SELECT'):
                error_msg = "出于安全考虑，只允许执行SELECT查询"
                logger.warning(f"⚠️  拒绝执行非SELECT查询: {query}")
                return {'success': False, 'error': error_msg}

            logger.debug(f"执行SQL查询: {query}")
            cursor.execute(query)

            # 判断是否是查询结果集
            if cursor.description:
                data = cursor.fetchall()
                # 转换datetime对象
                datetime_converted = 0
                for row in data:
                    for key, value in row.items():
                        if hasattr(value, 'strftime'):
                            row[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                            datetime_converted += 1

                result = {
                    'success': True,
                    'type': 'SELECT',
                    'data': data,
                    'columns': list(data[0].keys()) if data else [],
                    'row_count': len(data)
                }

                logger.info(f"✅ SELECT查询成功 - 返回 {len(data)} 行数据")
                if datetime_converted > 0:
                    logger.debug(f"转换了 {datetime_converted} 个datetime字段")
                logger.debug(f"查询结果列: {result['columns']}")

            else:
                result = {
                    'success': True,
                    'type': 'OTHER',
                    'affected_rows': cursor.rowcount,
                    'message': f'操作成功，影响 {cursor.rowcount} 行'
                }

                logger.info(f"✅ SQL操作成功 - 影响 {cursor.rowcount} 行")

            cursor.close()
            return result

        except Exception as e:
            error_msg = f"执行查询失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.debug(f"错误SQL: {query}")
            logger.debug(f"错误数据库: {database}")
            return {'success': False, 'error': str(e)}

    def get_table_info(self, database: str, table: str) -> Dict[str, Any]:
        """获取表的详细信息"""
        try:
            if not self.connect(database):
                return {'success': False, 'error': '数据库连接失败'}

            cursor = self.connection.cursor()

            # 获取表状态信息
            cursor.execute(f"SHOW TABLE STATUS LIKE '{table}'")
            table_status = cursor.fetchone()

            # 获取表结构
            structure = self.get_table_structure(database, table)

            # 获取数据统计
            data_info = self.get_table_data(database, table, limit=1)

            result = {
                'success': True,
                'name': table,
                'database': database,
                'engine': table_status.get('Engine') if table_status else None,
                'rows': table_status.get('Rows') if table_status else 0,
                'data_length': table_status.get('Data_length') if table_status else 0,
                'index_length': table_status.get('Index_length') if table_status else 0,
                'collation': table_status.get('Collation') if table_status else None,
                'comment': table_status.get('Comment') if table_status else None,
                'structure': structure,
                'total_count': data_info.get('total_count', 0)
            }

            cursor.close()
            logger.info(f"获取表 {table} 详细信息成功")
            return result

        except Exception as e:
            logger.error(f"获取表详细信息失败: {e}")
            return {'success': False, 'error': str(e)}

# 全局数据库管理器实例 - 使用环境变量配置
db_manager = DatabaseManager(DatabaseConfig.from_env())