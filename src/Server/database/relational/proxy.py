#!/usr/bin/python3

"""
On this file is present a class that serves has a proxy to the
communication to the database.

With it the code relative to this specific database type is only
present on this file and the other classes can be independent of
the database (in what concerns the connections)
"""

from mysql.connector.pooling import MySQLConnectionPool
from mysql.connector import errors

from database.relational import config
from database.exceptions import RelationalDBException, LogicException

# for password hashing
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.exceptions import InvalidKey
from base64 import b64encode, b64decode
from os import urandom

import datetime


class StoredProcedures:
    REGISTER_CLIENT = "insert_client"
    REGISTER_MEDIC = "insert_medic"
    GET_ALL_USERNAMES = "get_all_usernames"
    INSERT_DEVICE = "insert_device"
    GET_CREDENTIALS = "get_credentials"
    GET_ALL_CLIENT_DEVICES = "get_all_client_devices"
    GET_ALL_SUPPORTED_DEVICES = "get_all_supported_devices"
    GET_USER_PROFILE_DATA = "get_user_info"
    UPDATE_CLIENT_PROFILE_DATA = "update_client_info"
    UPDATE_MEDIC_PROFILE_DATA = "update_medic_info"
    INSERT_SLEEP_SESSION = "insert_sleep_session"
    GET_SLEEP_SESSIONS = "get_sleep_sessions"
    UPDATE_DEVICE = "update_device"
    DELETE_DEVICE = "delete_device"
    REQUEST_PERMISSION = "request_permission"
    GRANT_PERMISSION = "grant_permission"
    ACCEPT_PERMISSION = "accept_permission"
    REMOVE_ACCEPTED_PERMISSION = "remove_accepted_permission"
    REJECT_PERMISSION = "delete_permission"
    DELETE_PERMISSION = REJECT_PERMISSION
    HAS_PERMISSION = "has_permission"
    UPDATE_PERMISSIONS_USER = "update_permissions_user"
    GET_EXPIRED_PERMISSIONS_OF_USER = "get_expired_permissions"
    GET_PENDING_PERMISSIONS_OF_USER = "get_pending_permissions"
    GET_ACCEPTED_PERMISSIONS_OF_USER = "get_accepted_permissions"

SQL_STATE = "03000"

SALT_SIZE = 32

class MySqlProxy:
    """Proxy used to interact with a MySql database allowing ..."""

    def __init__(self,):
        """Constructs a pool of connection according to the config.py file"""
        self.__pool = MySQLConnectionPool(
            pool_name = config.POOL_NAME,
            pool_size = config.POOL_SIZE,
            host      = config.HOST,
            port      = config.PORT,
            database  = config.DATABASE,
            user      = config.USERNAME,
            password  = config.PASSWORD
        )

    @property
    def _pool(self):
        return self.__pool

    def _init_connection(self):
        """
        Gets a connection to the database from the pool, creating a cursor from it

        :return: :class:`PooledMySQLConnection` and :class:`MySQLCursor`
        :rtype: tuple
        """
        conn = self._pool.get_connection()
        cursor = conn.cursor()

        return conn, cursor

    def _close_conenction(self, conn, cursor):
        """
        Closes both the cursor and the connection. Because pooled connection are being used this
            is just returning the connection to the pool

        :param conn: connection object to the database
        :type conn: :class:`PooledMySQLConnection`
        :param cursor: cursor created from the connection object
        :type cursor: :class:`MySQLCursor`
        """
        cursor.close()
        conn.close()

    def _derive_password(self, password):
        """
        Derives a password with a salt

        :param password: clear text password
        :type password: str
        :return: derived password and salt used encoded in base64
        :rtype: (str, str)
        """
        salt = urandom(SALT_SIZE)

        password = bytes(password, "utf-8")

        kdf = Scrypt(
            salt    = salt,
            length  = 32,
            n       = 2**14,
            r       = 8,
            p       = 1,
            backend = default_backend()
        )

        derived_password = kdf.derive(password)

        return b64encode(derived_password), b64encode(salt)

    def _verify_password(self, password, derived_password, salt):
        """

        :param password: clear text received from the user that wants to be authenticated
        :param password: str
        :return: true if password received matches the one stored
        :rtype: bool
        """
        derived_password = b64decode(derived_password)
        salt = b64decode(salt)

        password = bytes(password, "utf-8")

        kdf = Scrypt(
            salt    = salt,
            length  = 32,
            n       = 2**14,
            r       = 8,
            p       = 1,
            backend = default_backend()
        )

        try:
            kdf.verify(password, derived_password)
            return True
        except InvalidKey:
            return False

    def register_client(self, username, password, full_name, email, health_number,
                              birth_date, weight, height, additional_information):
        """
        Creates a new user on the database. The `insert_client` SP is used to create all user related data.
        On this function the password is hashed to be stored.
        The write to the database can fail if an user with the same username exists or a
         client with the same health_number already exists.

        :raises Exception: In case if something goes wrong when calling stored procedures

        :param username: can't exist another user with the same value
        :type username: str
        :param password: clear text password to be hashed
        :type password: str
        :param full_name: full name of the client
        :type full_name: str
        :param email: email of the client
        :type email: str
        :param health_number: number used on the country of the client to identify him in which concerns the health
            department
        :type health_number: int
        :param birth_date: with format day-month-year
        :type birth_date: str
        :param weight: in kilograms (optional)
        :type weight: float
        :param height: in meters (optional)
        :type height: float
        :param additional_information: information that can be important to mention so a medic can be more contextualized
        (optional)
        :type additional_information: list
        :return: client_id of the client created on the database
        :rtype: int
        """
        try:
            conn, cursor = self._init_connection()

            password, salt = self._derive_password(password)

            cursor.callproc(
                StoredProcedures.REGISTER_CLIENT,
                (username, password, salt, full_name, email, health_number,
                 birth_date, weight, height, additional_information)
            )

            new_id = next(cursor.stored_results()).fetchall()[0][0]

            return new_id
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def register_medic(self, username, password, full_name, email, company, specialities):
        """
        Creates a new user on the database. The `insert_medic` SP is used to create all user related data.
        On this function the password is hashed to be stored.
        The write to the database can fail if an user with the same username already exists.

        :param username: of the medic
        :type username: str
        :param password: clear text password to be hashed
        :type password: str
        :param full_name: of the medic
        :type full_name: str
        :param email: of the medic
        :type email: str
        :param company: to which company is the medic working (optional)
        :type company: str
        :param specialities: medic specializations (optional)
        :type specialities: str
        :return: medic_id of the medic created on the database
        :rtype: int

        :raises Exception: In case if something goes wrong when calling stored procedures
        """
        try:
            conn, cursor = self._init_connection()

            password, salt = self._derive_password(password)

            cursor.callproc(
                StoredProcedures.REGISTER_MEDIC,
                (username, password, salt, full_name, email, company, specialities)
            )

            new_id = next(cursor.stored_results()).fetchall()[0][0]

            return new_id
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def check_credentials(self, username, password):
        """
        Verifies if the received credential are correct

        :param username: of a client or medic
        :type username: str
        :param password:
        :type password: str
        :return: 0 - invalid credentials, 1 - valid and its a client, 2 - valid and its a medic
        :rtype: (int, bool)
        """
        try:
            conn, cursor = self._init_connection()

            cursor.callproc(StoredProcedures.GET_CREDENTIALS, [username])
            user_type, derived_password, salt = next(cursor.stored_results()).fetchall()[0]

            if not user_type:
                return 0

            return user_type if self._verify_password(password, derived_password, salt) else 0
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def register_device(self, username, type, authentication_fields, latitude=None, longitude=None):
        """
        Inserts a new device on the database and associates it with the user

        :param username: client to associate
        :type username: str
        :param type: type of the device (brand + " " + model)
        :type type: str
        :param authentication_fields: fields to access device's APIs
        :type authentication_fields: list
        :param latitude: location of the device (only applicable for home devices)
        :type latitude: float
        :param longitude: location of the device (only applicable for home devices)
        :type longitude: float
        :return: id of the new device
        :rtype: int
        """
        try:
            auth_fields = [(name, value) for name, value in authentication_fields.items()]

            conn, cursor = self._init_connection()

            cursor.execute("CREATE TEMPORARY TABLE IF NOT EXISTS tmp_authentication_fields(name VARCHAR(30)," +
                                                                                          "value VARCHAR(500))")
            cursor.execute("DELETE FROM tmp_authentication_fields")
            cursor.executemany("INSERT INTO tmp_authentication_fields values (%s, %s)", auth_fields)
            cursor.callproc(StoredProcedures.INSERT_DEVICE, (username, type, latitude, longitude))

            conn.commit()

            return next(cursor.stored_results()).fetchall()[0][0]
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def get_all_devices_of_user(self, username):
        """
        Obtains all devices associated with the user with the same
        username as the one received from the arguments

        :param username: of the client
        :type username: str
        :return: info of all devices. In case of a home device the
        object will also contain a longitude and latitude field
        [{device:int, type:int, token:str, uuid:str}, ...]
        :rtype: list
        """
        try:
            conn, cursor = self._init_connection()

            cursor.callproc(StoredProcedures.GET_ALL_CLIENT_DEVICES, [username])

            devices = dict()
            for (device_id,
                 type_id,
                 type,
                 brand,
                 model,
                 photo, auth_field_name,
                        auth_field_value, latitude,
                                          longitude) in next(cursor.stored_results()).fetchall():
                if device_id not in devices.keys():
                    device = {
                        "id": device_id,
                        "type": "%s %s" % (brand, model),
                        "photo": photo,
                        "authentication_fields": {}
                    }
                    if latitude: # if one exist both exist
                        device["latitude"] = latitude
                        device["longitude"] = longitude
                    devices[device_id] = device

                if auth_field_name:
                    devices[device_id]["authentication_fields"][auth_field_name] = auth_field_value

            return list(devices.values())
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def get_all_supported_devices(self):
        """
        Retrieves all supported devices by the system giving also
        the metrics that that device can read

        :return: all information of the supported devices
        [{id:int, type:str, brand:str, model:str, metrics:[{name:str, unit:str}, ...]}, ...]
        :rtype: list
        """
        try:
            conn, cursor = self._init_connection()

            cursor.callproc(StoredProcedures.GET_ALL_SUPPORTED_DEVICES)

            retval = {}
            for (device_id, device_type, device_brand, device_model,
                 metric_name, metric_unit) in next(cursor.stored_results()).fetchall():
                if device_id not in retval.keys():
                    retval[device_id] = {
                        "id": device_id,
                        "type": device_type,
                        "brand": device_brand,
                        "model": device_model,
                        "metrics": []
                    }

                retval[device_id]["metrics"].append({ # TODO maybe append tuple instead of dict
                    "name": metric_name,
                    "unit": metric_unit
                })

            return list(retval.values())
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def get_user_profile_data(self, username):
        """
        Obtains all profile data associated with the username received

        :param username: of the client/medic to search for
        :type username: str
        :return: all client/medic's profile data
        {client_id:int, full_name:str, email:str, health_number:int, birth_date:datetime, weight:float, height:float}
        :rtype: dict
        """
        try:
            conn, cursor = self._init_connection()

            cursor.callproc(StoredProcedures.GET_USER_PROFILE_DATA, [username])

            results = next(cursor.stored_results()).fetchall()[0]

            if results[0] == "client":
                data = {key: "" if not results[i+1] else (results[i+1] if key != "birth_date" else results[i+1].strftime("%d-%m-%Y"))
                        for i, key in enumerate(["client_id",
                                                 "full_name",
                                                 "email",
                                                 "health_number",
                                                 "birth_date",
                                                 "weight",
                                                 "height",
                                                 "additional_info"])}
                data["user_type"] = "client"
            elif results[0] == "medic":
                data = {key: results[i+1] if results[i+1] else ""
                        for i, key in enumerate(["medic_id",
                                                 "full_name",
                                                 "email",
                                                 "company",
                                                 "specialities"])}
                data["user_type"] = "medic"
            else:
                raise Exception("Invalid user type")

            return data
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def update_client_profile_data(self, username, password, new_password, full_name, email,
                                         health_number, birth_date, weight, height, additional_information):
        """
        Updates the profile information for a user. The function receives all information
        to overload all data, assuming that some of it is the same as the stored one.

        :param username: of the client to update the data
        :type username: str
        :param password: old clear text password
        :type password: str
        :param new_password: new clear text password
        :type new_password: str
        :param full_name: full name of the client
        :type full_name: str
        :param email: email of the client
        :type email: str
        :param health_number: number used on the country of the client to identify him in which concerns the health
            department
        :type health_number: int
        :param birth_date: with format dd-mm-yyyy
        :type birth_date: str
        :param weight: in kilograms
        :type weight: float
        :param height: in meters
        :type height: float
        :param additional_information: information that can be important to mention so a medic can be more contextualized
        :type additional_information: str
        """
        try:
            conn, cursor = self._init_connection()

            if password and new_password:
                cursor.callproc(StoredProcedures.GET_CREDENTIALS, [username])
                user_type, derived_password, salt = next(cursor.stored_results()).fetchall()[0]

                if not self._verify_password(password, derived_password, salt):
                    raise errors.Error("Wrong password!", sqlstate=SQL_STATE)

                new_password, new_salt = self._derive_password(new_password)
            else:
                new_password, new_salt = None, None

            cursor.callproc(StoredProcedures.UPDATE_CLIENT_PROFILE_DATA, (username, new_password, new_salt,
                                                                          full_name, email, health_number,
                                                                          birth_date, weight, height,
                                                                          additional_information))
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def update_medic_profile_data(self, username, password, new_password,
                                        full_name, email, company, specialities):
        """
        Updates the profile information for a user. The function receives all information
        to overload all data, assuming that some of it is the same as the stored one.

        :param username: of the client to update the data
        :type username: str
        :param password: old clear text password
        :type password: str
        :param new_password: new clear text password
        :type new_password: str
        :param full_name: full name of the client
        :type full_name: str
        :param email: email of the client
        :type email: str
        :param company: to which company is the medic working
        :type company: str
        :param specialities: medic specializations
        :type specialities: str
        """
        try:
            conn, cursor = self._init_connection()

            if password and new_password:
                cursor.callproc(StoredProcedures.GET_CREDENTIALS, [username])
                user_type, derived_password, salt = next(cursor.stored_results()).fetchall()[0]

                if not self._verify_password(password, derived_password, salt):
                    raise LogicException("Wrong password!")

                new_password, new_salt = self._derive_password(new_password)
            else:
                new_password, new_salt = None, None

            cursor.callproc(StoredProcedures.UPDATE_MEDIC_PROFILE_DATA, (username, new_password, new_salt,
                                                                         full_name, email, company, specialities))
            conn.commit()
        except LogicException:
            raise
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def insert_sleep_session(self, username, day, duration, begin, end):
        """
        Register a new sleep session on the database. Can fail if the new session
        overlaps with existing ones in which concerns begin and end time

        :param username: of the client
        :type username: str
        :param day:
        :type day: datetime.date
        :param duration: seconds
        :type duration: int
        :param begin:
        :type begin: datetime.datetime
        :param end:
        :type end: datetime.datetime
        """
        try:
            conn, cursor = self._init_connection()

            cursor.callproc(StoredProcedures.INSERT_SLEEP_SESSION, (username, day, duration, begin, end))

            conn.commit()
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def get_sleep_sessions(self, username, begin=None, end=None):
        """
        Get information of the sleep session that belongs to the days within the interval
        of the dates received on the arguments

        :param username: of the client
        :type username: str
        :param begin: all sleep sesisons after this date
        :type begin: datetime.date
        :param end: all sleep sessions before this date
        :type end: datetime.date
        :return: information of all sleep sessions that respect the arguments received
        :rtype: list
        """
        try:
            conn, cursor = self._init_connection()

            cursor.callproc(StoredProcedures.GET_SLEEP_SESSIONS, (username, begin, end))

            return next(cursor.stored_results()).fetchall()
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def get_all_usernames(self):
        """
        Used by the main server to get all username so he can start to
        quety data from devices/external api's

        :return: list of all usernames OF CLIENTS
        :rtype: list
        """
        try:
            conn, cursor = self._init_connection()

            cursor.callproc(StoredProcedures.GET_ALL_USERNAMES)

            return [username[0] for username in next(cursor.stored_results()).fetchall()]
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def updtate_device(self, username, device_id, data):
        """
        Update information, authentication fields, of a device associated with a client

        :param username: of the client
        :type username: str
        :param device_id: of the device owned by the client
            to change data
        :type device_id: int
        :param data: fields to change (authentication fields and/or longitude, latitude)
        :type data: dict
        """
        try:
            latitude, longitude = None, None
            if "latitude" in data.keys(): # assume that if latitude is in dict, longitude is also
                latitude = data["latitude"]
                longitude = data["longitude"]

            auth_fields = [(name, value) for name, value in data["authentication_fields"].items()]

            conn, cursor = self._init_connection()

            cursor.execute("CREATE TEMPORARY TABLE IF NOT EXISTS tmp_authentication_fields(name VARCHAR(30)," +
                           "value VARCHAR(500))")
            cursor.execute("DELETE FROM tmp_authentication_fields")
            cursor.executemany("INSERT INTO tmp_authentication_fields values (%s, %s)", auth_fields)
            cursor.callproc(StoredProcedures.UPDATE_DEVICE, (username, device_id, latitude, longitude))

            conn.commit()
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def delete_device(self, username, device_id):
        """
        Deassociates a device from a user deleting any information associated with the device

        :param username: of the client
        :type username: str
        :param device_id: id of the device to delete
        :type device_id: int
        """
        try:
            conn, cursor = self._init_connection()

            cursor.callproc(StoredProcedures.DELETE_DEVICE, (username, device_id))
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def request_permission(self, medic, client, health_number, duration):
        """
        A medic requests temporary permission to see a client's data

        :param medic: username of the medic
        :type medic: str
        :param client: username of the client
        :type client: str
        :param duration: for how long the permission will be up
        :type duration: datetime.timedelta
        :return: information of source and destination intervenients of the permission
        :rtype: (dict, dict)
        """
        try:
            conn, cursor = self._init_connection()

            cursor.callproc(StoredProcedures.REQUEST_PERMISSION, (medic, client, health_number, duration))

            stored_results = cursor.stored_results()

            destinationResult = next(stored_results).fetchall()[0]
            destination = {key: destinationResult[ind] for ind, key in enumerate(["username", "name", "email", "health_number"])}

            sourceResult = next(stored_results).fetchall()[0]
            source = {key: sourceResult[ind] for ind, key in enumerate(["username", "name", "email", "company"])}
            source["duration"] = str(duration)[:-3]

            return source, destination
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def delete_request_permission(self, medic, client):
        """
        Allows a medic to delete a request permission done previously

        :param medic: username of the medic
        :type medic: str
        :param client: username of the client
        :type client: str
        """
        try:
            conn, cursor = self._init_connection()

            cursor.callproc(StoredProcedures.DELETE_PERMISSION, (client, medic))
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def grant_permission(self, client, medic, duration):
        """
        A clients grants temporary permission to a medic to let him see his data

        :param client: username of the client
        :type client: str
        :param medic: username of the client
        :type medic: str
        :param duration: for how long the permission will be up
        :type duration: datetime.timedelta
        """
        try:
            conn, cursor = self._init_connection()

            cursor.callproc(StoredProcedures.GRANT_PERMISSION, (client, medic, duration))

            stored_results = cursor.stored_results()

            destinationResult = next(stored_results).fetchall()[0]
            destination = {key: destinationResult[ind] for ind, key in enumerate(["name", "email", "company"])}

            sourceResult = next(stored_results).fetchall()[0]
            source = {key: sourceResult[ind] for ind, key in enumerate(["username", "name", "email", "health_number"])}
            source["duration"] = str(duration)[:-3]

            return source, destination
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def accept_permission(self, client, medic):
        """
        A client accepts a pending request created by a medic to see his data

        :param client: username of the client
        :type client: str
        :param medic: username of the medic
        :type medic: str
        """
        try:
            conn, cursor = self._init_connection()

            cursor.callproc(StoredProcedures.ACCEPT_PERMISSION, (client, medic))
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def remove_accepted_permission(self, client, medic):
        """
        Allows a client to delete an accepted permission

        :param client: username of the medic
        :type client: str
        :param medic: username of the medic
        :type medic: str
        """
        try:
            conn, cursor = self._init_connection()

            cursor.callproc(StoredProcedures.REMOVE_ACCEPTED_PERMISSION, (client, medic))
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def reject_permission(self, client, medic):
        """
        A client rejects a pending request created by a medic to see his data

        :param client: username of the client
        :type client: str
        :param medic: username of the medic
        :type medic: str
        """
        try:
            conn, cursor = self._init_connection()

            cursor.callproc(StoredProcedures.REJECT_PERMISSION, (client, medic))
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def has_permission(self, medic, client):
        """
        Verifies if a medic [still] has access to client's data

        :param medic:
        :type medic: str
        :param client:
        :type client: str
        :return: true if it has, false otherwise
        :rtype: bool
        """
        try:
            conn, cursor = self._init_connection()

            cursor.callproc(StoredProcedures.HAS_PERMISSION, (medic, client))

            return next(cursor.stored_results()).fetchall()[0][0] == 1
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def _parse_permissions_data(self, data, type):
        """
        Parses permission's data from a list of tuples
        to a list of dictionaries for each type of permission

        :param data: data returned from the database
        :type data: list
        :param type: diferent types of permissions have different fields. With
            this argument conditionals can be done so this method handles each one
            different
        0 pending
        1 accepted
        3 expired
        :type type: int
        :return: parsed data
        :rtype: list
        """
        return_value = []
        if type in [0, 1]:
            for duration, username, full_name, email, neutral in data:
                return_value.append({
                    "duration": duration,
                    "username": username,
                    "name": full_name,
                    "email": email,
                    "health_number": neutral,
                    "company": neutral
                })

        elif type == 2:
            for begin_date, \
                last_date, username, full_name, email, neutral in data:
                permission = {
                    "begin_date": begin_date,
                    "end_date": last_date,
                    "username": username,
                    "name": full_name,
                    "email": email,
                    "health_number": neutral,
                    "company": neutral
                }

                return_value.append(permission)

        else:
            raise TypeError("type argument can only be one of these (0, 1, 2)")

        return return_value

    def get_pending_permissions(self, user):
        """
        Gets existing pending permissions

        :param user: username
        :type user: str
        :return: all pending permissions associated with a user
        :rtype: list
        """
        try:
            conn, cursor = self._init_connection()

            conn.start_transaction()

            cursor.callproc(StoredProcedures.UPDATE_PERMISSIONS_USER, [user])
            is_medic = next(cursor.stored_results()).fetchall()[0][0] == 1

            cursor.callproc(StoredProcedures.GET_PENDING_PERMISSIONS_OF_USER, (user, is_medic))

            conn.commit()

            return self._parse_permissions_data(next(cursor.stored_results()).fetchall(), 0)
        except Exception as e:
            if isinstance(e, errors.Error) and e.sqlstate == SQL_STATE:
                raise LogicException(e.msg)
            raise RelationalDBException(str(e))
        finally:
            self._close_conenction(conn, cursor)

    def get_all_permissions_data(self, user):
        """
        Gets existing permissions of the three types of permissions to display on the permissions page.

        :param user: username
        :type user: str
        :return: lists of the three types of permissions
        :rtype: dict
        """
        try:
            conn, cursor = self._init_connection()

            data = {}

            conn.start_transaction()
            cursor.callproc(StoredProcedures.UPDATE_PERMISSIONS_USER, [user])
            is_medic = next(cursor.stored_results()).fetchall()[0][0] == 1

            cursor.callproc(StoredProcedures.GET_PENDING_PERMISSIONS_OF_USER, (user, is_medic))
            data["pending"] = self._parse_permissions_data(next(cursor.stored_results()).fetchall(), 0)

            cursor.callproc(StoredProcedures.GET_ACCEPTED_PERMISSIONS_OF_USER, (user, is_medic))
            data["accepted"] = self._parse_permissions_data(next(cursor.stored_results()).fetchall(), 1)

            cursor.callproc(StoredProcedures.GET_EXPIRED_PERMISSIONS_OF_USER, (user, is_medic))
            data["expired"] = self._parse_permissions_data(next(cursor.stored_results()).fetchall(), 2)

            conn.commit()

            return data
        finally:
            self._close_conenction(conn, cursor)
