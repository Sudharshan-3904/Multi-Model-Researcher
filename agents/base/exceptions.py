"""
Custom exceptions for agent errors and system faults.
"""
class AgentError(Exception):
    pass

class CommunicationError(Exception):
    pass

class AuthenticationError(Exception):
    pass

class TaskExecutionError(Exception):
    pass
