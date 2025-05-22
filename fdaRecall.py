import streamlit as st
import requests
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static


api_key = st.secrets["FDA_key"]

st.title("🍴🚨 Food Recall Finder")

# Sidebar with user input for state, date, food-brand, ongoing recalls
with st.sidebar:
    st.subheader("Search for recalls by applying the following filters")


    state = st.selectbox(
            "Select state:*",
            ("AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA",
             "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
             "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"),
            index = None,
            placeholder="Select a state...",
    )

    date = st.date_input("Select a date range: ", [],
                         datetime.date(2004,1,1),
                         datetime.date.today() - datetime.timedelta(days=14),
                         format="MM.DD.YYYY"
                         )

    food_brand = st.text_input("Enter a specific food or brand:", placeholder="e.g. cheese, Heinz")

    status = st.checkbox("Show only on-going recalls", value=False)

    submit = st.button("Get Recall")

#State is a mandatory field
if submit and state:
    start_date = ""
    end_date = ""


    if date:
        if len(date) == 2:
            start_date = (f"{date[0].year}"
                          f"{date[0].month if date[0].month > 9 else "0" + str(date[0].month)}"
                          f"{date[0].day if date[0].day > 9 else "0" + str(date[0].day)}"
                          )

            end_date = (f"{date[1].year}"
                        f"{date[1].month if date[1].month > 9 else "0" + str(date[1].month)}"
                        f"{date[1].day if date[1].day > 9 else "0" + str(date[1].day)}"
                        )
        elif len(date) == 1:
            start_date = (f"{date[0].year}"
                          f"{date[0].month if date[0].month > 9 else "0" + str(date[0].month)}"
                          f"{date[0].day if date[0].day > 9 else "0" + str(date[0].day)}"
                          )
            end_date = start_date
    #get recalls
    url = (f"https://api.fda.gov/food/enforcement.json?api_key={api_key}&"
           f"search=distribution_pattern:{state}"
           f"{"+AND+report_date:["+start_date+"+TO+"+end_date+"]" if date != () else "" }"
           f"{"+AND+product_description:"+food_brand if food_brand else ""}"
           f"{"" if not status else "+AND+status:'Ongoing'"}"
           f"&sort=report_date:desc&limit=500"
           )

    response = requests.get(url)

    if response.status_code == 200:

        response = response.json()["results"]

        columns = ['status','product_description','distribution_pattern','classification', 'recalling_firm','voluntary_mandated', 'product_quantity', 'reason_for_recall','recall_initiation_date','termination_date']

        table = pd.DataFrame(response, columns=columns)
        st.success("Recall data found successfully! Displaying the most recent entries first.")


        st.dataframe(table) #Interactive table with all recalls

        #Bar chart for classifications
        counts = table['classification'].value_counts()


        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(counts.index, counts.values)
        ax.set_title("Counts of Recall Severity by Classification")
        st.pyplot(fig)

        #Expander with classification explanations
        with st.expander("Classification Details"):
            st.markdown("**Class I**: Dangerous or defective products that predictably could cause serious health problems or death.")
            st.markdown("**Class II**: Products that might cause a temporary health problem, or pose only a slight threat of a serious nature.")
            st.markdown("**Class III**: Products that are unlikely to cause any adverse health reaction, but that violate FDA labeling or manufacturing laws. ")


        st.subheader(f"Supermarkets in selected area: {state}")
        st.info(f"Displaying supermarkets.")

        df = pd.read_csv('states.csv') #csv with radius, lat, lon for each state

        #radius, lat, and long for selected state
        areaDF = df[df["state"] == state]

        radius = areaDF.iat[0,1]
        latitude = areaDF.iat[0,2]
        longitude = areaDF.iat[0,3]

        #Getting supermarkets in the state
        def find_supermarkets(rad, lat, lon):
            supermarkets = []

            overpass_url = "https://overpass-api.de/api/interpreter"
            query = f"""
            [out:json];
            (
              node["shop"="supermarket"](around:{rad},{lat},{lon});
            );
            out;
            """

            response2 = requests.post(overpass_url, data=query)

            if response2.status_code == 200:
                data = response2.json()

                for element in data['elements']:
                    supermarkets.append([f"{element.get('tags', {}).get('name', 'Unknown')}", f"{element['lat']}", f"{element['lon']}"])

                return supermarkets
            else:
                st.error("Error fetching supermarkets in given area.")


        # Map displaying supermarkets in the state
        def map_creator(supermarkets):
            m = folium.Map(location=[supermarkets[0][1], supermarkets[0][2]], zoom_start=4)

            for name, latitude, longitude in supermarkets:
                name = name.replace("`", "'")
                folium.Marker([latitude, longitude], popup=name, tooltip=name).add_to(m)

            folium_static(m)

        supermarkets_lst = find_supermarkets(radius, latitude, longitude)

        #check if there are supermarkets in the state to plot
        if len(supermarkets_lst) > 0:
            map_creator(supermarkets_lst)

        else:
            st.warning("Error: no supermarkets found in the area.")


    else:
        st.error(f"Error: Could not retrieve data for selected filters. Try redefining your search or using broader criteria.")


elif submit and not state:
    st.warning("Please select a state.")
