#!/usr/bin/env python3
"""
智能运维助手 - 日志配置模块
提供统一的日志记录功能，支持文件日志、控制台日志和错误追踪
"""

import os
import sys
import logging
import logging.handlers
import traceback
import functools
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Callable
from config import Config


class LoggerSetup:
    """日志系统配置类"""

    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        # 日志文件路径
        self.app_log_file = self.log_dir / "app.log"
        self.error_log_file = self.log_dir / "error.log"
        self.debug_log_file = self.log_dir / "debug.log"

        # 日志级别
        self.log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)

    def setup_logger(self, name: str = __name__) -> logging.Logger:
        """设置并返回配置好的logger"""
        logger = logging.getLogger(name)

        # 避免重复添加handler
        if logger.handlers:
            return logger

        logger.setLevel(self.log_level)

        # 创建格式器
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 应用日志文件处理器
        app_handler = logging.handlers.RotatingFileHandler(
            self.app_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        app_handler.setLevel(logging.INFO)
        app_handler.setFormatter(formatter)
        logger.addHandler(app_handler)

        # 错误日志文件处理器
        error_handler = logging.handlers.RotatingFileHandler(
            self.error_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

        # 调试日志文件处理器（仅在DEBUG模式下）
        if self.log_level <= logging.DEBUG:
            debug_handler = logging.handlers.RotatingFileHandler(
                self.debug_log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=3,
                encoding='utf-8'
            )
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(formatter)
            logger.addHandler(debug_handler)

        return logger


class ErrorTracker:
    """错误追踪和记录类"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log_exception(self,
                     exception: Exception,
                     context: str = "",
                     extra_data: Optional[dict] = None):
        """记录异常详细信息"""
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "context": context,
            "traceback": traceback.format_exc(),
            "extra_data": extra_data or {}
        }

        # 记录到错误日志
        self.logger.error(
            f"异常发生 - 上下文: {context}\n"
            f"异常类型: {error_info['exception_type']}\n"
            f"异常信息: {error_info['exception_message']}\n"
            f"额外数据: {error_info['extra_data']}\n"
            f"堆栈追踪:\n{error_info['traceback']}"
        )

        return error_info

    def log_function_error(self,
                          func_name: str,
                          args: tuple,
                          kwargs: dict,
                          exception: Exception):
        """记录函数执行错误"""
        error_info = {
            "function": func_name,
            "args": str(args),
            "kwargs": str(kwargs),
            "error": str(exception),
            "timestamp": datetime.now().isoformat()
        }

        self.logger.error(
            f"函数执行错误 - {func_name}\n"
            f"参数: args={args}, kwargs={kwargs}\n"
            f"错误: {exception}\n"
            f"堆栈: {traceback.format_exc()}"
        )

        return error_info


def error_logger(context: str = "", log_args: bool = True):
    """错误日志装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            error_tracker = ErrorTracker(logger)

            try:
                # 记录函数开始执行
                if log_args:
                    logger.debug(f"开始执行函数: {func.__name__}, args={args}, kwargs={kwargs}")
                else:
                    logger.debug(f"开始执行函数: {func.__name__}")

                result = func(*args, **kwargs)

                logger.debug(f"函数执行成功: {func.__name__}")
                return result

            except Exception as e:
                # 记录错误信息
                error_context = f"{context} - 函数: {func.__name__}" if context else f"函数: {func.__name__}"
                error_tracker.log_function_error(func.__name__, args, kwargs, e)

                # 重新抛出异常
                raise

        return wrapper
    return decorator


def async_error_logger(context: str = "", log_args: bool = True):
    """异步错误日志装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger = get_logger()
            error_tracker = ErrorTracker(logger)

            try:
                # 记录函数开始执行
                if log_args:
                    logger.debug(f"开始执行异步函数: {func.__name__}, args={args}, kwargs={kwargs}")
                else:
                    logger.debug(f"开始执行异步函数: {func.__name__}")

                result = await func(*args, **kwargs)

                logger.debug(f"异步函数执行成功: {func.__name__}")
                return result

            except Exception as e:
                # 记录错误信息
                error_context = f"{context} - 异步函数: {func.__name__}" if context else f"异步函数: {func.__name__}"
                error_tracker.log_function_error(func.__name__, args, kwargs, e)

                # 重新抛出异常
                raise

        return wrapper
    return decorator


# 全局logger实例
_logger_setup = LoggerSetup()
_app_logger = None

def get_logger(name: str = None) -> logging.Logger:
    """获取logger实例"""
    global _app_logger
    if _app_logger is None or name:
        _app_logger = _logger_setup.setup_logger(name or "yunwei_app")
    return _app_logger


def log_system_info():
    """记录系统启动信息"""
    logger = get_logger()
    logger.info("=" * 60)
    logger.info("智能运维助手系统启动")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info(f"日志级别: {Config.LOG_LEVEL}")
    logger.info(f"日志目录: {_logger_setup.log_dir}")
    logger.info("=" * 60)


def log_operation(operation: str,
                  details: dict = None,
                  level: str = "info",
                  user: str = "system"):
    """记录操作日志"""
    logger = get_logger()

    log_message = f"[{user}] {operation}"
    if details:
        log_message += f" - 详情: {details}"

    log_method = getattr(logger, level.lower(), logger.info)
    log_method(log_message)


def log_performance(func_name: str,
                   start_time: float,
                   end_time: float,
                   details: dict = None):
    """记录性能日志"""
    logger = get_logger()
    duration = end_time - start_time

    perf_info = {
        "function": func_name,
        "duration": f"{duration:.3f}s",
        "details": details or {}
    }

    logger.info(f"性能记录 - {perf_info}")


# 初始化日志系统
if __name__ != "__main__":
    # 当作为模块导入时自动初始化
    log_system_info()