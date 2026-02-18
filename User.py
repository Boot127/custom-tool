#Yong jun , 252176E, group4 
class User:
    def __init__(self, user_id, username, email, first_name, last_name, phone='', 
                 address='', role='customer', profile_image=None, created_at=None, 
                 last_login=None, is_active=True):
        self.__user_id = user_id
        self.__username = username
        self.__email = email
        self.__first_name = first_name
        self.__last_name = last_name
        self.__phone = phone
        self.__address = address
        self.__role = role
        self.__profile_image = profile_image
        self.__created_at = created_at
        self.__last_login = last_login
        self.__is_active = is_active

    def get_user_id(self):
        return self.__user_id

    def get_username(self):
        return self.__username

    def get_email(self):
        return self.__email

    def get_first_name(self):
        return self.__first_name

    def get_last_name(self):
        return self.__last_name

    def get_full_name(self):
        return f"{self.__first_name} {self.__last_name}"

    def get_phone(self):
        return self.__phone

    def get_address(self):
        return self.__address

    def get_role(self):
        return self.__role

    def get_profile_image(self):
        return self.__profile_image

    def get_created_at(self):
        return self.__created_at

    def get_last_login(self):
        return self.__last_login

    def is_active(self):
        return self.__is_active

    def is_admin(self):
        return self.__role == 'admin'

    @classmethod
    def from_database_row(cls, row_data):
        if len(row_data) >= 11:
            return cls(
                user_id=row_data[0],
                username=row_data[1],
                email=row_data[2],
                first_name=row_data[3],
                last_name=row_data[4],
                phone=row_data[5] if row_data[5] else '',
                address=row_data[6] if row_data[6] else '',
                role=row_data[7],
                profile_image=row_data[8],
                created_at=row_data[9],
                last_login=row_data[10],
                is_active=True if len(row_data) > 11 and row_data[11] == 1 else False
            )
        return None

    def to_dict(self):
        return {
            'user_id': self.__user_id,
            'username': self.__username,
            'email': self.__email,
            'first_name': self.__first_name,
            'last_name': self.__last_name,
            'full_name': self.get_full_name(),
            'phone': self.__phone,
            'address': self.__address,
            'role': self.__role,
            'profile_image': self.__profile_image,
            'created_at': self.__created_at,
            'last_login': self.__last_login,
            'is_active': self.__is_active
        }