import streamlit as st
import easyocr
import base64
import re
import pandas as pd
import mysql.connector
from PIL import Image
from io import BytesIO

st.set_page_config(layout='wide')
st.title('BizCardX - Extracting Business Card Data with OCR')
tab1, tab2, tab3 = st.tabs(['Upload Image - Extract Image - Store it in Database', 'Data from DB', 'Operation in Database'])

# Function to retrieve data from the database
def get_data_from_db():
    # Database Connection
    connect_mysql = mysql.connector.connect(
        host='127.0.0.1',
        port=3303,
        user='root',
        password='root'
    )
    mycursor = connect_mysql.cursor()
    mycursor.execute('CREATE DATABASE IF NOT EXISTS bizcardx_db')
    mycursor.execute('USE bizcardx_db')
    mycursor.execute('CREATE TABLE IF NOT EXISTS extracted_data(id INT AUTO_INCREMENT PRIMARY KEY, company_name VARCHAR(255), card_holder_name VARCHAR(255), designation VARCHAR(255), mobile_number VARCHAR(255), email_id VARCHAR(255), website_url VARCHAR(255), area VARCHAR(255), city VARCHAR(255), state VARCHAR(255), pincode VARCHAR(255), image_data LONGBLOB)')

    # Get column names from the table
    mycursor.execute('SHOW columns FROM extracted_data')
    columns = [col[0] for col in mycursor.fetchall()] 

    # Prepare column names for the SELECT statement
    columns_with_id = ', '.join(columns)

    # Retrieve data from the database
    mycursor.execute(f'SELECT DISTINCT {columns_with_id} FROM extracted_data')
    data = mycursor.fetchall()
    df = pd.DataFrame(data, columns=columns)

    return df

with tab1:
    st.write('To upload the image for Data Extraction click on the below button')
    upload_file = st.file_uploader('Upload File', type=['png', 'jpg','jpeg'])
    if upload_file is not None:
        # Read the uploaded file as bytes
        image_data = upload_file.read()
        # Convert bytes to image for display
        image = Image.open(BytesIO(image_data))
        st.write('The uploaded Image is:')
        st.image(image, caption='Uploaded Image', use_column_width=False)

        extract_btn = st.button('Extract Data & Database Storage')
        if extract_btn:
            reader = easyocr.Reader(['en'])
            result = reader.readtext(image_data)

            company_name = ""
            card_holder_name = ""
            designation = ""
            mobile_numbers = ""
            email_address = ""
            website_url = ""
            area = ""
            city = ""
            state = ""
            pin_code = ""

            card_info = [i[1] for i in result]
            card = ' '.join(card_info)
            replacement = [
            (";", ""),
            (',', ''),
            ("WWW ", "www."),
            ("www ", "www."),
            ('www', 'www.'),
            ('www.', 'www'),
            ('wwW', 'www'),
            ('wWW', 'www'),
            ('.com', 'com'),
            ('com', '.com'),
            ]

            for old, new in replacement:
                card = card.replace(old, new)
            # st.write(card)

            for items in result:
                text = items[1]
                # Card Holder Name
                card_holder_name_ptrn = r'^[A-Za-z]+ [A-Za-z]+$|^[A-Za-z]+$|^[A-Za-z]+ & [A-Za-z]+$'
                name = []
                for i in card_info:
                    if re.findall(card_holder_name_ptrn, i):
                        if i not in 'WWW':
                            name.append(i)
                            card = card.replace(i, '')
                card_holder_name = name[0]

                # Designation
                designation = name[1]

                #Company Name
                if len(name) == 3:
                    company_name = name[2]
                else:
                    company_name = name[2] + ' ' + name[3]

                # PINCODE
                if re.search(r'\b\d{6}|6004513\b', text):
                    pin_code = re.search(r'\b\d{6}|6004513\b', text).group(0)

                # Phone
                ph_ptrn = r"\+*\d{2,3}-\d{3}-\d{4}"
                ph = re.findall(ph_ptrn, text)
                for num in ph:
                    mobile_numbers += num + ' '

                # Mail
                if re.match(r"[^@]+@[^@]+\.[^@]+", text):
                    email_address = text

                #Website URL
                website_match = re.search(r'(www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,})', card)
                if website_match:
                    website_url = website_match.group(1)

                    #Area
                area_ptrn = re.search(r'\b\d{3} .+? St|^global\b', text)
                if area_ptrn:
                    area = area_ptrn.group(0)
                    area = area.replace(' St', '')

                #City
                new = card.split()
                # st.write(new)
                if new[4] == 'St':
                    city = new[2]
                elif new[8] == 'St': 
                    city = new[5]
                elif new[2] == 'St':
                    city = new[3]
                else:
                    city = new[7]

                #State
                state_ptrn = re.search(r'\bTamilNadu\b', text)
                if state_ptrn:
                    state = state_ptrn.group()
            #Display the Results
            mobile_numbers_str = mobile_numbers.strip()
            image_base64 = base64.b64encode(image_data).decode()

            extract_data = {
                            'company_name': [company_name],
                            'card_holder_name': [card_holder_name],
                            'designation': [designation],
                            'mobile_number': [mobile_numbers_str],
                            'email_id': [email_address],
                            'website_url': [website_url],
                            'area': [area],
                            'city': [city],
                            'state': [state],
                            'pincode': [pin_code],
                            'image_data': [image_base64]
            }
            st.dataframe(extract_data)
            
            # extract_data.update({'image_data': [image_base64]})  
            #extract_data_df = pd.DataFrame(extract_data)
            #Database Connection...
            connect_mysql = mysql.connector.connect(
                                host = '127.0.0.1',
                                port = 3303,
                                user = 'root',
                                password = 'root',
                                )              
            mycursor = connect_mysql.cursor()
            #Create DB...
            mycursor.execute('CREATE DATABASE IF NOT EXISTS bizcardx_db')
            mycursor.execute('USE bizcardx_db')
            mycursor.execute('CREATE TABLE IF NOT EXISTS extracted_data(id INT AUTO_INCREMENT PRIMARY KEY, company_name VARCHAR(255), card_holder_name VARCHAR(255), designation VARCHAR(255), mobile_number VARCHAR(255), email_id VARCHAR(255), website_url VARCHAR(255), area VARCHAR(255), city VARCHAR(255), state VARCHAR(255), pincode VARCHAR(255), image_data LONGBLOB)')
            insert_query = '''INSERT INTO extracted_data (company_name, card_holder_name, designation, mobile_number, 
                                email_id, website_url, area, city, state, pincode, image_data) 
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
            data = (
                company_name, card_holder_name, designation, mobile_numbers.strip(), email_address, website_url,
                area, city, state, pin_code, image_base64
            )
            mycursor.execute(insert_query, data)
            connect_mysql.commit()
            st.success('Successfully Stored in Database!!!')

with tab2:
    st.write('Data in the Database:')
    data = get_data_from_db()
    st.dataframe(data)
    for index, row in data.iterrows():
        image_base64 = row['image_data']
        image_bytes = base64.b64decode(image_base64)
        image = Image.open(BytesIO(image_bytes))
        st.image(image, caption=f"Image {index + 1}", use_column_width=False)

with tab3:
    st.write('In our Application we can Perform CURD operation choose any one operation')
    dropdown_curd_operation = st.selectbox('Select a CURD Opeartion',('Select Option', 'Add', 'Read', 'Update', 'Delete'))
    if dropdown_curd_operation == 'Add':
        st.write('Add Data to Database:')
        company_name = st.text_input('Company Name')
        card_holder_name = st.text_input('Card Holder Name')
        designation = st.text_input('Designation')
        mobile_numbers = st.text_input('Mobile Number')
        email_address = st.text_input('Email ID')
        website_url = st.text_input('Website URL')
        area = st.text_input('Area')
        city = st.text_input('City')
        state = st.text_input('State')
        pin_code = st.text_input('PINCODE')
        uploaded_file = st.file_uploader('Upload Image')

        if st.button('Submit'):
            if company_name and card_holder_name and designation and mobile_numbers and email_address and website_url and area and city and state and pin_code and uploaded_file:
                # Read the uploaded file as bytes
                image_data = uploaded_file.read()
                image_base64 = base64.b64encode(image_data).decode()

                # Database Connection
                connect_mysql = mysql.connector.connect(
                    host='127.0.0.1',
                    port=3303,
                    user='root',
                    password='root',
                    database='bizcardx_db'
                )
                mycursor = connect_mysql.cursor()

                # Insert data into the database
                insert_query = '''INSERT INTO extracted_data (company_name, card_holder_name, designation, mobile_number, 
                                email_id, website_url, area, city, state, pincode, image_data) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
                data = (company_name, card_holder_name, designation, mobile_numbers.strip(), email_address, website_url,
                        area, city, state, pin_code, image_base64)
                try:
                    mycursor.execute(insert_query, data)
                    connect_mysql.commit()
                    st.success('Data Added Successfully!')
                except mysql.connector.Error as err:
                    st.error(f"Error: {err}")
                finally:
                    mycursor.close()
                    connect_mysql.close()
            else:
                st.error('All fields are required.')

    elif dropdown_curd_operation == 'Read':
        st.write('Data in the Database:')
        data = get_data_from_db()
        st.dataframe(data)

    elif dropdown_curd_operation == 'Update':
        st.write('Update Data in the Database:')
    
        # Dropdown to select record to update
        selected_record_id = st.selectbox('Select Record to Update', data['id'].tolist())
        
        # Input fields for updating attributes
        updated_company_name = st.text_input('Company Name', data.loc[data['id'] == selected_record_id, 'company_name'].values[0])
        updated_card_holder_name = st.text_input('Card Holder Name', data.loc[data['id'] == selected_record_id, 'card_holder_name'].values[0])
        updated_designation = st.text_input('Designation', data.loc[data['id'] == selected_record_id, 'designation'].values[0])
        # ... Add input fields for other attributes similarly

        if st.button('Update'):
            if updated_company_name and updated_card_holder_name and updated_designation:
                # Database Connection
                connect_mysql = mysql.connector.connect(
                    host='127.0.0.1',
                    port=3303,
                    user='root',
                    password='root',
                    database='bizcardx_db'
                )
                mycursor = connect_mysql.cursor()

                # Update data in the database
                update_query = '''UPDATE extracted_data 
                                SET company_name = %s, card_holder_name = %s, designation = %s
                                WHERE id = %s'''
                updated_data = (updated_company_name, updated_card_holder_name, updated_designation, selected_record_id)
                try:
                    mycursor.execute(update_query, updated_data)
                    connect_mysql.commit()
                    st.success('Data Updated Successfully!')
                except mysql.connector.Error as err:
                    st.error(f"Error: {err}")
                finally:
                    mycursor.close()
                    connect_mysql.close()
            else:
                st.error('All fields are required for update.')    
    elif dropdown_curd_operation == 'Delete':
        st.write('Delete Data from the Database:')
        # Dropdown to select record to delete
        selected_record_id = st.selectbox('Select Record to Delete', data['id'].tolist())
        selected_record_company_name = data.loc[data['id'] == selected_record_id, 'company_name'].values[0]
        
        # Display the selected record information
        st.write(f'Deleting record with ID: {selected_record_id}, Company Name: {selected_record_company_name}')
        
        if st.button('Delete'):
            # Database Connection
            connect_mysql = mysql.connector.connect(
                host='127.0.0.1',
                port=3303,
                user='root',
                password='root',
                database='bizcardx_db'
            )
            mycursor = connect_mysql.cursor()

            # Delete data from the database
            delete_query = '''DELETE FROM extracted_data WHERE id = %s'''
            try:
                mycursor.execute(delete_query, (selected_record_id,))
                connect_mysql.commit()
                st.success('Data Deleted Successfully!')
            except mysql.connector.Error as err:
                st.error(f"Error: {err}")
            finally:
                mycursor.close()
                connect_mysql.close()
