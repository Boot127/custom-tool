# ==================== IMPORTS ====================
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, DateField, BooleanField, SelectField, FileField, SubmitField, FloatField
from wtforms.validators import Email, Optional, DataRequired, Length, EqualTo, Regexp, NumberRange, URL
from datetime import datetime
# =================================================

# ==================== REGISTRATION FORM ====================
# Yong jun , 252176E, group4
class RegistrationForm(FlaskForm):
    username = StringField('Username', [
        DataRequired(message="Username is required"),
        Length(min=4, max=25, message="Username must be between 4 and 25 characters"),
        Regexp(r'^[A-Za-z0-9_]+$', message="Username can only contain letters, numbers, and underscores")
    ], render_kw={"placeholder": "Choose a username"})
    
    email = StringField('Email Address', [
        DataRequired(message="Email is required"),
        Length(max=100),
        Email(message="Please enter a valid email address")
    ], render_kw={"placeholder": "Enter your email"})
    
    email_otp = StringField('Email OTP', [
        DataRequired(message="OTP is required"),
        Length(min=6, max=6, message="OTP must be 6 digits"),
        Regexp(r'^\d{6}$', message="OTP must contain only numbers")
    ], render_kw={"placeholder": "Enter 6-digit OTP"})
    
    password = PasswordField('Password', [
        DataRequired(message="Password is required"),
        Length(min=8, message="Password must be at least 8 characters long"),
        Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
                         message="Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character")
    ], render_kw={"placeholder": "Create a strong password"})
    
    confirm_password = PasswordField('Confirm Password', [
        DataRequired(message="Please confirm your password"),
        EqualTo('password', message="Passwords must match")
    ], render_kw={"placeholder": "Confirm your password"})
    
    first_name = StringField('First Name', [
        DataRequired(message="First name is required"),
        Length(min=2, max=50, message="First name must be between 2 and 50 characters")
    ])
    
    last_name = StringField('Last Name', [
        DataRequired(message="Last name is required"),
        Length(min=2, max=50, message="Last name must be between 2 and 50 characters")
    ])
    
    date_of_birth = DateField('Date of Birth', [Optional()], format='%Y-%m-%d')
    phone = StringField('Phone Number', [Optional()])
    address = TextAreaField('Address', [Optional()])

# ==================== LOGIN FORM ====================
# Yong jun , 252176E, group4
class LoginForm(FlaskForm):
    username = StringField('Username', [DataRequired()])
    password = PasswordField('Password', [DataRequired()])
    remember_me = BooleanField('Remember Me')

# ==================== PROFILE FORM ====================
# Yong jun , 252176E, group4
class ProfileForm(FlaskForm):
    username = StringField('Username', [
        DataRequired(message="Username is required"),
        Length(min=4, max=25, message="Username must be between 4 and 25 characters"),
        Regexp(r'^[A-Za-z0-9_]+$', message="Username can only contain letters, numbers, and underscores")
    ], render_kw={"placeholder": "Choose a username"})
    first_name = StringField('First Name', [DataRequired()])
    last_name = StringField('Last Name', [DataRequired()])
    email = StringField('Email', [DataRequired(), Email()])
    email_otp = StringField('Email Verification OTP', [
        Optional(),
        Length(min=6, max=6, message="OTP must be 6 digits"),
        Regexp(r'^\d{6}$', message="OTP must contain only numbers")
    ], render_kw={"placeholder": "Enter 6-digit OTP (required if changing email)"})
    date_of_birth = DateField('Date of Birth', [Optional()], format='%Y-%m-%d')
    phone = StringField('Phone Number', [
        Optional(),
        Regexp(r'^[0-9+\-\s()]+$', message="Phone number can only contain numbers, +, -, spaces, and parentheses")
    ], render_kw={"placeholder": "Enter phone number (numbers only)"})
    address = TextAreaField('Address', [Optional()])

# ==================== CHANGE PASSWORD FORM ====================
# Yong jun , 252176E, group4
class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', [DataRequired()])
    new_password = PasswordField('New Password', [
        DataRequired(), 
        Length(min=8, message="Password must be at least 8 characters long"),
        Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
               message="Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character")
    ])
    confirm_password = PasswordField('Confirm New Password', [
        DataRequired(), 
        EqualTo('new_password', message='Passwords must match')
    ])

# ==================== CONTACT FORM ====================
# Yong jun , 252176E, group4
class ContactForm(FlaskForm):
    name = StringField('Name', [DataRequired()])
    email = StringField('Email', [DataRequired(), Email()])
    order_id = StringField('Order ID (Optional)', [Optional()])
    issue_type = SelectField('Issue Type', choices=[
        ('order', 'Order Related'),
        ('return', 'Return/Exchange'),
        ('defect', 'Product Defect'),
        ('other', 'Other')
    ])
    priority = SelectField('Priority', choices=[('low', 'Low'), ('normal', 'Normal'), ('high', 'High')])
    message = TextAreaField('Message', [DataRequired(), Length(min=10)])
    attachments = FileField('Attach Files (Optional)')
    consent = BooleanField('I consent to the storage of my data', [DataRequired()])

# ==================== PRODUCT FORM ====================
# Thylis, 251684J, group 4
class ProductForm(FlaskForm):
    name = StringField('Product Name', 
                       validators=[DataRequired(), Length(min=2, max=100)])
    
    category = SelectField('Category', 
                          choices=[
                              ('', 'Select Category'),
                              ('T-Shirts & Apparel', 'T-Shirts & Apparel'),
                              ('Drinkware', 'Drinkware'),
                              ('Accessories', 'Accessories')
                          ],
                          validators=[DataRequired()])
    
    description = TextAreaField('Description', 
                               validators=[DataRequired(), Length(min=10, max=500)])
    
    base_price = FloatField('Base Price ($)', 
                           validators=[DataRequired(), NumberRange(min=0.01)])
    
    image_url = StringField('Image URL', 
                           validators=[DataRequired(), URL(), Length(max=255)])
    
    customizable = BooleanField('Customizable', default=True)
    
    in_stock = BooleanField('In Stock', default=True)
    
    submit = SubmitField('Save Product')

# ==================== PRODUCT SEARCH FORM ====================
# Thylis, 251684J, group 4
class ProductSearchForm(FlaskForm):
    search = StringField('Search', validators=[Optional()])
    category = SelectField('Category', 
                          choices=[
                              ('', 'All Categories'),
                              ('T-Shirts & Apparel', 'T-Shirts & Apparel'),
                              ('Drinkware', 'Drinkware'),
                              ('Accessories', 'Accessories')
                          ])
    in_stock = SelectField('Stock Status', 
                          choices=[
                              ('', 'All'),
                              ('1', 'In Stock'),
                              ('0', 'Out of Stock')
                          ])
    submit = SubmitField('Filter')