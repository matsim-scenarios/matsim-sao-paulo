from tqdm import tqdm
import pandas as pd
import numpy as np
import geopandas as gpd
import pyreadstat
import os

def configure(context):
    context.config("data_path")    
    context.config("census_file")
def execute(context):

    columns = ['V0001', 'V0011', 'V0221', 'V0222', 'V0601', 'V6036', 'V0401', 'V1004', 'V0010', 'V0641', 'V0642', 'V0643', 'V0644', 'V0628', 'V6529', 'V0504']

    CHUNK_SIZE = 500000 

    # Read the file in chunks
    reader = pyreadstat.read_file_in_chunks(pyreadstat.read_sav, "%s/Census/%s" % (context.config("data_path"), context.config("census_file")), chunksize= CHUNK_SIZE, usecols=columns)
    #reader = pd.read_spss("%s/Census/Censo.2010.brasil.amostra.10porcento.sav" % context.config("data_path"))

    # Get column names and create output dataframe
    df, meta = pyreadstat.read_sav("%s/Census/%s" % (context.config("data_path"), context.config("census_file")), row_offset=1, row_limit=1,usecols=columns)
    df_census = pd.DataFrame(columns = df.columns)
    
    # Fill in the output dataframe with relevant observations from chunks
    i = CHUNK_SIZE
    dfs = []
    for df, meta in reader:
    	# Keep only those in Sao Paulo state
        df1 = df[df["V0001"] == '35']
        df_census = pd.concat([df_census, df1])
        print("Processed " + repr(i) + " samples.")
        i = i + CHUNK_SIZE

    # Renaming
    df_census.columns = ["federationCode", "areaCode", "householdWeight", "metropolitanRegion", "personNumber", "gender", "age", "goingToSchool", "employment", "onLeave", "helpsInWork", "farmWork", "householdIncome", "motorcycleAvailability", "carAvailability", "numberOfMembers"]

    # The following step only concerns children
    df_census['employment'] = df_census['employment'].fillna(2.0) 

    # Assume households do not have access to a car if not reported
    df_census['carAvailability'] = df_census['carAvailability'].fillna(2.0) 

    # Assume households do not have access to a motorcycle if not reported
    df_census['motorcycleAvailability'] = df_census['motorcycleAvailability'].fillna(2.0)

    # Adjust weights after dropping out observations with non filled necessary attributes  
    total_weight = df_census["householdWeight"].sum()
    df_census = df_census.dropna(subset=['householdIncome', 'age', 'gender', 'carAvailability', 'motorcycleAvailability' ])
    new_weight = df_census["householdWeight"].sum()
    df_census["householdWeight"] = df_census["householdWeight"] * (total_weight / new_weight)

    # Adjust "student" status for erroneous observations
    df_census.loc[((df_census["goingToSchool"] == 1) | (df_census["goingToSchool"] == 2)) & ~(df_census["employment"] == 1), "employment"] = 3

    # Put person IDs
    df_census.loc[:, "person_id"] = df_census.index
    df_census.loc[:, "weight"] = df_census["householdWeight"]

    # Spatial
    df_census["zone_id"] = df_census["areaCode"]
    return df_census


def validate(context):
    if not os.path.exists("%s/Census/Censo.2010.brasil.amostra.10porcento.sav" % context.config("data_path")):
        raise RuntimeError("Census 2010 not available.")

    return os.path.getsize("%s/Census/Censo.2010.brasil.amostra.10porcento.sav" % context.config("data_path"))
