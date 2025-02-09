## Load Packages

import selenium
import pandas as pd
import regex 
import numpy as np

from datetime import datetime
import json
import os
import re
import time
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

## Create a Function to webscrape Goodreads 'to-read' data

# Function to dismiss the text box by clicking the close button
def dismiss_text_box(browser):
    try:
#         modal = WebDriverWait(browser, 5).until(
#         EC.presence_of_element_located((By.CSS_SELECTOR, "div.modal.modal__content"))
#     )
#         print("Modal is visible!")
    
        # Locate the modal close button inside the div with class 'modal__close'
        dismiss_button = WebDriverWait(browser, 2).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "div.modal__close button.gr-iconButton"))
    )
        
        # Scroll the dismiss button into view to make it interactable
        #browser.execute_script("arguments[0].scrollIntoView(true);", dismiss_button)
        

        # Click the dismiss button
        dismiss_button.click()
        print("Dismissed the text box/pop-up.")
        
    except Exception as e:
        print(f"No dismiss button found or error: {e}")
        
        try:
            close_button_js = browser.find_element(By.CSS_SELECTOR, "div.modal__close button.gr-iconButton")
            browser.execute_script("arguments[0].click();", close_button_js)
            print("Popup closed successfully using JavaScript.")
        except Exception as js_error:
            print(f"Error in JavaScript click: {js_error}")

## Webscrape Goodreads to-read list 

def get_to_read_data(url):

    opts = Options()
    opts.add_argument("--headless")
    browser = webdriver.Firefox(options=opts)
    
    browser.get(url)
    
    # Dismiss any pop-ups when you first go on the site
    dismiss_text_box(browser)
    
    print('dismissed initially!')
    
    # Initialize lists to store book titles, authors, and hrefs
    book_titles = []
    book_links = []  # This will store the hrefs
    authors = []  # This will store the authors

    # Loop to go through all pages
    while True:
        # Find all <a> tags for book titles (excluding <a> tags with class)
        # the <a> tags with class will not contain the titles on the page 
        
        a_tags = browser.find_elements(By.TAG_NAME, "a")

        # Get all the book titles and their links (excluding <a> tags with class)
        for a_tag in a_tags:
            title = a_tag.get_attribute("title")  # Extract the title attribute
            class_name = a_tag.get_attribute("class")  # Get the class attribute
            href = a_tag.get_attribute("href")  # Extract the href attribute

            # Only include if there is a title and no class attribute
            if title and not class_name:
                book_titles.append(title)
                book_links.append(href)  # Store the href if the conditions are met

        # Get all authors' names (only from the <td> tags with class 'field author')
        author_tags = browser.find_elements(By.CSS_SELECTOR, "td.field.author .value a")
        for author_tag in author_tags:
            author_name = author_tag.text  # Extract the author name
            authors.append(author_name)

        # Check if the "next" page link exists
        next_page = browser.find_elements(By.CSS_SELECTOR, "a.next_page")

        if not next_page:  # If no next page exists, exit the loop
            break

        # Dismiss the text box after clicking the next page link
        dismiss_text_box(browser)

        # Click the next page link to load the next page
        next_page[0].click()

        # Wait for the next page to load (adjusted to 10 seconds)
        time.sleep(0.5)  # Wait for 2 seconds before clicking the next page

    # Turn data into a dataframe
    book_dat = pd.DataFrame({'Title':book_titles,'Author':authors,'Link':book_links})
    
    # Close the browser
    browser.quit()
    
    return book_dat

## Find the common books between all the to-read lists

def find_overlapping_rows(dataframes_dict):
    # Filter out empty dataframes from the dictionary
    dataframes = [df for df in dataframes_dict.values() if not df.empty]
    
    # Check if there are no non-empty dataframes
    if not dataframes:
        return pd.DataFrame()  # Return an empty DataFrame if all are empty
    
    # First, find rows that are common across all dataframes
    # Start by setting the first dataframe as the base
    overlapping_rows = dataframes[0]
    
    # Iterate over the remaining dataframes to find the intersection
    for df in dataframes[1:]:
        overlapping_rows = pd.merge(overlapping_rows, df, how='inner')
    
    # Check if there are overlapping rows across all dataframes
    if not overlapping_rows.empty:
        return overlapping_rows
    
    # If no rows overlap across all dataframes, find the majority overlap
    # Concatenate all dataframes and count occurrences of each row
    concatenated = pd.concat(dataframes, ignore_index=True)
    
    print('concatenated!')
    
    # Calculate the majority threshold dynamically (rounded up)
    majority_threshold = int(np.ceil(len(dataframes) / 2))
    
    # Group by 'Title', 'Author', and 'Link', and count the occurrences of each group
    grouped_df = concatenated.groupby(['Title', 'Author', 'Link']).size().reset_index(name='Count')
    
    print('grouped!')

    # Filter the books that have a count greater than or equal to the majority threshold
    filtered_books = grouped_df[grouped_df['Count'] >= majority_threshold]
    
    print('filtered!')
    
    ## should I include a manual override? Like it only has to appear in two lists
    
    # If no rows meet the majority condition
    if filtered_books.empty:
        return "There are no majority overlaps!"
    
    else:
        return filtered_books

## Function to see if the URLs are valid "to-read" URLS

def check_urls(urls):
    # Regular expression to match the valid URL pattern
    pattern = r"^https://www.goodreads.com/review/list/\d+\?shelf=to-read$"

    valid_urls = []
    invalid_urls = []
    
    for url in urls:
        if re.match(pattern, url):
            valid_urls.append(url)
        else:
            invalid_urls.append(url)
    
    return valid_urls, invalid_urls

#!pip install dash

from dash import Dash, dcc, html, Input, Output, State, ALL,no_update,callback
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from dash import dash_table
import pandas as pd
import re

# Initialize the Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], prevent_initial_callbacks=True, suppress_callback_exceptions=True)

server = app.server

# Layout for the form page with outer margin
app.layout = html.Div(
    style={
        'margin': '20px',  # Add margin around the whole page
        'padding': '20px',  # Optional: Padding inside the page for more space around elements
        'maxWidth': '1200px',  # Optional: Limit the maximum width of the page
        'marginLeft': 'auto',  # Center the layout horizontally
        'marginRight': 'auto',  # Center the layout horizontally
    },
    children=[
        # Title at the top
        html.H1("Next BookClub Book Generator", style={"text-align": "center", "margin-top": "20px"}),

        # Instructions Section
        html.Div(
            children=[
                html.H3("Instructions of Use", style={"font-weight": "bold"}),
                html.Ol(
                    children=[
                        html.Li("Enter the number of members in your bookclub that have a Goodreads. Note: If you change the number later on, you will have to re-enter all the URLs."),
                        html.Li(["Enter the URL to your each member's Goodreads' to-read list to each of the input boxes. (Click on your Profile -> Look for your Bookshelves -> Click 'to-read'). The URL should look something like 'https://www.goodreads.com/user/show/186644225?shelf=to-read'. Your Goodreads profile must be PUBLIC. ",
                               html.A('Here are instructions to make your profile public.', href='https://help.goodreads.com/s/article/How-do-I-edit-my-privacy-settings-1553870936907')]),
                        html.Li("Click 'Submit' to get a list of books that the members of your book club have overlapping. If there are no books that overlap between all members, then books that appear in the majority of the member's lists will be returned. If there are no books that appear in the majority of the member's list, then no results will be returned."),
                        html.Li("Browse through the suggested books to find your next read!"),
                    ]
                ),
            ],
            style={"padding": "20px", "background-color": "#f8f9fa", "border-radius": "8px"}
        ),
        # Input for the number of URLs
        html.H3("How many URLs are you providing?",
               style={"padding": "20px","border-radius": "8px"}),
        
        # Input field aligned with the Instructions box
        html.Div(
            children=[
                html.Label("Enter number of URLs:", style={"font-weight": "bold"}),
                dcc.Input(
                    id='url-count-input', 
                    type='number', 
                    min=2, 
                    value=2, 
                    style={'margin-top': '10px', 'width': '100px'}
                ),
            ],
            style={"text-align": "center", "margin-bottom": "20px"}
        ),
        
        # A div to hold the dynamically generated URL input fields
        html.Div(id='url-inputs-container',style={"padding": "20px","border-radius": "8px"}),
        
        # Submit Button
        html.Div(
            dbc.Button("Submit", id="submit-button", color="primary", size="lg", className="mt-4"),
            style={'display': 'flex', 'justify-content': 'center'}
        ),
        
        # Loading Spinner and "Please wait" text
        dcc.Loading(
            id="loading-spinner",
            type="default",  # This can be 'circle', 'dot', or 'default' (a bar)
            children=[
                # Output message above the result table
                html.Div(
                    id="output-message",  # New container for the "Here are the similar books!" message
                    children=[],  # Initially empty
                    style={'textAlign': 'center', 'fontSize': '20px', 'marginTop': '20px', 'fontWeight': 'bold'}
                ),
                html.Div(
                    id="output-container", 
                    style={'marginTop': '30px'}  # Add margin-top to create space between the spinner and the message
                ),
                html.Div(
                    id="please-wait-message",  # Add an ID for the "Please wait" message
                    children=[],  # Initially leave it empty
                    style={'textAlign': 'center', 'marginTop': '30px'}  # Style the message
                ),
                
            ]
        ),
        
        # Spacer between content and footer
        html.Div(style={"height": "50px"}),
        
        # Footer with disclaimer and author's note
        html.Div(
            children=[
                html.P(
                    "Disclaimer: This is a book suggestion tool powered by Goodreads data. "
                    "It is not affiliated with Goodreads.", 
                    style={"font-size": "small", "text-align": "center", "color": "#6c757d"}
                ),
                html.P(
                    "Author's Note: As someone that is a part of many book clubs, it's always a hassle trying to find the next book for the club to read. I created this tool for me to easily see which books I have in common with other book club members! Hope you enjoy this tool.",
                    style={"font-size": "small", "text-align": "center", "color": "#6c757d"}
                ),
            ],
            style={"margin-top": "40px"}
        ),

        # Links at the bottom right corner
        html.Div(
            children=[
                html.A("My LinkedIn", href="https://www.linkedin.com", target="_blank", style={"margin-right": "15px", "font-size": "small"}),
                html.A("My Github", href="https://www.github.com", target="_blank", style={"font-size": "small"}),
            ],
            style={
                "position": "fixed",  # Fix the links to the bottom right of the page
                "bottom": "10px",     # Position 10px from the bottom
                "right": "10px",      # Position 10px from the right
                "z-index": "100",     # Ensure links are above other elements
            }
        )
    ]
)

# Callback to generate URL input fields dynamically
@app.callback(
    Output('url-inputs-container', 'children'),
    [Input('url-count-input', 'value')]
)
def generate_url_inputs(url_count):
    if url_count is None or url_count <= 0:
        return []
    
    # Generate the URL input fields based on the count
    url_inputs = [
        dbc.Input(id={'type': 'url-input', 'index': i}, placeholder=f'Enter URL #{i+1}', type='url', className="mb-2") 
        for i in range(url_count)
    ]
    
    return url_inputs

# Pattern Matching Callback to handle the form submission and process URLs into a DataFrame
@app.callback(
    [Output('output-container', 'children'),
     Output('please-wait-message', 'children'), # Now, we also update the "Please wait" message
    Output('output-message', 'children')],  
    [Input('submit-button', 'n_clicks')],
    [State({'type': 'url-input', 'index': ALL}, 'value')]  # Using ALL to capture all URL inputs dynamically
)
def handle_submit(n_clicks, url_values):
    if n_clicks is None:
        raise PreventUpdate
    
    # Initially, set the "Please wait..." message after the submit button is clicked
    please_wait_message = "Please wait..."
    
    # Filter out None or empty values for URLs
    urls = [url for url in url_values if url]
    
    if not urls:
        return "Please enter at least one valid URL.", "",""  # Return an empty message if no URLs are entered  
    
    # Check if urls are valid 'to-read' urls
    # Output the results
    valid_urls,invalid_urls = check_urls(urls)
    
    if invalid_urls!=[]:
        return f"Please make sure you are entering a to-read list URLs. The following are not valid URLs:{invalid_urls}","",""

    
    # Simulate a long-running backend program (replace with your actual backend processing)
    import time
    time.sleep(1)  # Simulate delay (replace this with real backend code)
    
    # Backend
    d = {}
    url_cnt = 0
    for url in urls:

        ## Call the function and dynamically update the key for the dictionary
        d["book_dat{0}".format(url_cnt)] = get_to_read_data(url)

        ## Cycle through to the next link
        url_cnt+=1

    result = find_overlapping_rows(d)
    print('results!')
    print(result)
    
    if isinstance(result, pd.DataFrame):
        print('hitting results')
        # After processing, hide the "Please wait" message and show the result
        result_table = dash_table.DataTable(
            id='result-table',
            columns=[{'name': col, 'id': col} for col in result.columns],
            data=result.to_dict('records'),  # Convert the DataFrame to a list of dictionaries
            style_table={'height': '300px', 'overflowY': 'auto'},  # Optional styling for scrolling
            style_cell={'textAlign': 'center'},  # Optional: Center align text in the table
        )

        # Display a message above the result table
        output_message = "Here are the similar books!"  # This message will be displayed above the table

        return result_table, "", output_message
        
    
    elif result == 'There are no majority overlaps!':
        print('hitting no result')
        no_result_table = dash_table.DataTable(
            id='no_result-table',
            style_table={'height': '300px', 'overflowY': 'auto'},  # Optional styling for scrolling
            style_cell={'textAlign': 'center'},  # Optional: Center align text in the table
        )
        return no_result_table,"",result
        
    else:
        print('hitting edge case!')
        return "",result


# Run the app
if __name__ == '__main__':
    app.run_server(debug=True, jupyter_mode='tab')
