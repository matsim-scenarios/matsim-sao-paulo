from tqdm import tqdm
import pandas as pd
import numpy as np
import geopandas as gpd
import shapely.geometry as geo
from simpledbf import Dbf5
import time

def configure(context):
    context.stage("data.spatial.zones")
    context.config("data_path")    

def execute(context):
	
    dbf = Dbf5("%s/HTS/OD_2017.dbf" %  context.config("data_path"))
    df = dbf.to_dataframe()
	
    df_reduced = df[["ID_PESS","ZONA","IDADE","SEXO",
                "FE_PESS","FE_VIA",
                "CD_ATIVI","VL_REN_I","DIA_SEM",
                "ZONA_O","CO_O_X","CO_O_Y","MOTIVO_O",
                "ZONA_D","CO_D_X","CO_D_Y","MOTIVO_D",
                "MODOPRIN","MODO1",
                "H_SAIDA","MIN_SAIDA",
                "H_CHEG","MIN_CHEG",
                "DURACAO","QT_AUTO","QT_BICICLE","QT_MOTO","N_VIAG",
                "RENDA_FA", "PAG_VIAG", "TP_ESAUTO", "VL_EST","TIPVG", "CO_DOM_X", "CO_DOM_Y", "ESTUDA"]]	
    # rename columns
    df_reduced.columns = ["person_id","zone","age","gender",
                     "weight_person","weight_trip",
                     "employed","personal_income","weekday",
                     "origin_zone","origin_x","origin_y","origin_purpose",
                     "destination_zone","destination_x","destination_y","destination_purpose",
                     "mode","Mode1",
                     "departure_h","departure_m",
                     "arrival_h","arrival_m",
                     "duration","number_of_cars","number_of_bikes","number_of_motorcycles","trip_id",
                     "household_income", "trip_paid_by", "parking_type", "parking_cost",
                     "mode_type", "homeCoordX", "homeCoordY", "studying"]
    
    personColumnsToclean = ["person_id", "weight_person", "number_of_cars"]
    df_persons = df_reduced.drop_duplicates(subset ="person_id", 
                     keep = 'first', inplace = False)
    KeepColummnsPersons = ["person_id","age","gender", "zone",
                              "weight_person",
                              "employed","personal_income","number_of_cars",
                              "household_income", 
                              "trip_paid_by", "parking_type", "parking_cost", 
                              "mode_type", "homeCoordX", "homeCoordY", "studying"]


    df_persons = df_persons[KeepColummnsPersons]

    df_persons = df_persons.dropna(subset = personColumnsToclean, inplace = False)
    df_persons['employed'] = df_persons['employed'].map({1 : "yes", 2 : "yes", 
                                                     3 : "yes", 4 : "no", 5 : "no", 
                                                     6 : "no", 7 : "no", 8 : "student"})
    df_persons.loc[(~(df_persons["studying"]== 1)) & (df_persons['employed']=='no'), "employed"] = "student"
    
    columnsToClean = ["person_id", "weight_person","origin_zone",
                     "origin_x","origin_y","origin_purpose",
                     "destination_zone","destination_x",
                     "destination_y","destination_purpose",
                     "mode",
                     "departure_h","departure_m",
                     "arrival_h","arrival_m",
                     "duration","number_of_cars","trip_id"]  
    KeepColummnsTrips = ["person_id", "origin_zone", "origin_purpose", "origin_x", "origin_y", 
                     "destination_zone", "destination_x", "destination_y", "destination_purpose","mode",
                     "departure_h","departure_m",
                     "arrival_h","arrival_m", "duration","trip_id", 
                     "trip_paid_by", "homeCoordX", "homeCoordY"]                 
    df_cleaned = df_reduced.dropna(subset = columnsToClean, inplace = False)
    df_trips = df_cleaned[KeepColummnsTrips]
    df_trips['origin_purpose'] = df_trips['origin_purpose'].map({1 : "work", 2 : "work", 3 : "work", 
                                                                 4 : "education", 5 : "shopping",  
                                                                 6 : "errand", 7 : "leisure", 
                                                                 8 : "home", 9 : "errand", 
                                                                 10 : "errand", 11 : "leisure"})

    df_trips['destination_purpose'] = df_trips['destination_purpose'].map({1 : "work", 2 : "work", 3 : "work", 
                                                                 4 : "education", 5 : "shopping",  
                                                                 6 : "errand", 7 : "leisure", 
                                                                 8 : "home", 9 : "errand", 
                                                                 10 : "errand", 11 : "leisure"})

    df_trips['mode'] = df_trips['mode'].map({1 : "pt", 2 : "pt", 3 : "pt", 4 : "pt", 5 : "pt", 6 : "pt", 7 : "pt", 8 : "pt", 9 : "car", 10 : "car_passenger", 
                                             11 : "taxi", 12 : "ride_hailing", 13 : "motorcycle", 14 : "motorcycle", 15 : "bike", 16 : "walk", 17 : "other"})
                                                     
    #remove all things that are na and that could affect later stages
    df_cleaned = df_reduced.dropna(subset = columnsToClean, inplace = False)
   

    print("Filling %d/%d observations with number_of_cars = 0" % (np.sum(df_persons["number_of_cars"].isna()), len(df_persons)))
    df_persons["number_of_cars"] = df_persons["number_of_cars"].fillna(0.0)
    df_persons["number_of_cars"] = df_persons["number_of_cars"].astype(np.int)

    # ID and weight
    #df_persons.loc[:, "person_id"] = df_persons["observation"]
    df_persons.loc[:, "weight"] = df_persons["weight_person"]

    # Attributes
    df_persons.loc[df_persons["gender"] == 1, "sex"] = "male"
    df_persons.loc[df_persons["gender"] == 2, "sex"] = "female"
    df_persons["sex"] = df_persons["sex"].astype("category")
    df_persons["has_pt_subscription"] = df_persons["trip_paid_by"] == 3.0
    df_persons.loc[df_persons["trip_paid_by"] == 2.0, "has_pt_subscription"] = True

    df_persons["employment"] = df_persons["employed"]
    df_persons["employment"] = df_persons["employment"].astype("category")

    df_persons["age"] = df_persons["age"].astype(np.int)
    df_persons["binary_car_availability"] = df_persons["number_of_cars"] > 0
    df_persons["income"] = df_persons["personal_income"]
    
    df_zones = context.stage("data.spatial.zones")[0][["zone_id", "geometry"]]
    df_persons["geometry"] = [geo.Point(*xy) for xy in zip(df_persons["homeCoordX"], df_persons["homeCoordY"])]
    df_geo = gpd.GeoDataFrame(df_persons, crs = {"init" : "epsg:29183"})
    # only take necessary rows into account to speed up process
    home_zones = gpd.sjoin(df_geo[["person_id","geometry"]], df_zones[["zone_id","geometry"]], op = "within",how="left")
    # we ensure with the sjoin how="left" parameter, that GEOID is in the correct order
    df_persons["home_zone"] = home_zones["zone_id"]
    
    zone_id = df_persons["home_zone"].values.tolist()

     # Import shapefiles defining the different zones
    center = gpd.read_file("%s/Spatial/SC2010_RMSP_CEM_V3_merged_center.shp" % context.config("data_path"))
    center = center["AP_2010_CH"].values.tolist()
    city = gpd.read_file("%s/Spatial/SC2010_RMSP_CEM_V3_merged_city.shp" % context.config("data_path"))
    city = city["AP_2010_CH"].values.tolist()
    county = gpd.read_file("%s/Spatial/SC2010_RMSP_CEM_V3_merged_all_state.shp" % context.config("data_path"))
    county = county["AP_2010_CH"].values.tolist()

    # New localization variable: 3 in the city center, 2 in the Sao-Paulo city and 1 otherwise
    sp_area = [3 * (z in center) + 2 * (z in city and z not in center) + 1 * (z in county and z not in city) for z in zone_id]
    df_persons["residence_area_index"] = sp_area


    # Clean up
    df_persons = df_persons[[
        "person_id", "weight",
        "age", "sex", "employment", "binary_car_availability", "has_pt_subscription", "home_zone", "household_income", "residence_area_index"
    ]]

    # Trips

    df_trips.loc[df_trips["destination_purpose"] == "shopping", "destination_purpose"] = "shop"
    df_trips.loc[df_trips["destination_purpose"] == "errand", "destination_purpose"] = "other"

    df_trips.loc[df_trips["destination_purpose"].isna(), "destination_purpose"] = "other"
    df_trips["following_purpose"] = df_trips["destination_purpose"].astype("category")
    df_trips["preceeding_purpose"] = df_trips["origin_purpose"].astype("category")
    df_trips.loc[df_trips["mode"] == "motorcycle", "mode"] = "car"
    df_trips.loc[df_trips["mode"] == "taxi", "mode"] = "taxi"
    df_trips.loc[df_trips["mode"] == "ride_hailing", "mode"] = "taxi"
    df_trips.loc[df_trips["mode"] == "bike", "mode"] = "walk"

    df_trips.loc[df_trips["mode"] == "other", "mode"] = "walk"
    df_trips["mode"] = df_trips["mode"].astype("category")

    df_trips["departure_time"] = df_trips["departure_h"] * 3600.0 + df_trips["departure_m"] * 60.0
    df_trips["arrival_time"] = df_trips["arrival_h"] * 3600.0 + df_trips["arrival_m"] * 60.0

    # Remove trips from home to home
    hhtrips_index_list = df_trips.index[np.logical_and(df_trips["origin_purpose"]=="home", df_trips["destination_purpose"]=="home")] 
    hhtrips_index = df_trips.index.isin(hhtrips_index_list)
    df_trips = df_trips[~hhtrips_index]

    # Remove trips that are the first done by an agent not starting from home
    first_index_list = df_trips.index[np.logical_and(df_trips["trip_id"]==1, df_trips["origin_purpose"]!="home")] 
    first_index = df_trips.index.isin(first_index_list)
    to_remove1 = df_trips[first_index]
    df_trips = df_trips[~first_index]

    # Remove trips that are the last done by an agent not returning to home
    number_of_trips_per_agent = df_trips.groupby(["person_id"], sort=False)["trip_id"].max()
    is_last_trip_index = [df_trips["trip_id"].iloc[i] == number_of_trips_per_agent[df_trips["person_id"].iloc[i]]  for i in range(len(df_trips)) ]
    last_index_list = df_trips.index[np.logical_and(is_last_trip_index, df_trips["destination_purpose"]!="home")] 
    last_index = df_trips.index.isin(last_index_list)
    to_remove2 = df_trips[last_index]
    df_trips = df_trips[~last_index]

    # Remove agents concerned by one of the two previous cases
    agents_to_be_removed = pd.concat([to_remove1, to_remove2]).drop_duplicates()["person_id"].values.tolist()
    agents_list = [(df_persons["person_id"].iloc[i] not in agents_to_be_removed) for i in range(len(df_persons))]
    agents_index_list = df_persons.index[agents_list]
    agents_index = df_persons.index.isin(agents_index_list)
    df_persons = df_persons[agents_index]

    # Crowfly distance
    df_trips["crowfly_distance"] = np.sqrt(
        (df_trips["origin_x"] - df_trips["destination_x"])**2 + (df_trips["origin_y"] - df_trips["destination_y"])**2
    )

    # Adjust trip id
    df_trips = df_trips.sort_values(by = ["person_id", "trip_id"])
    trips_per_person = df_trips.groupby("person_id").size().reset_index(name = "count")["count"].values
    df_trips["new_trip_id"] = np.hstack([np.arange(n) for n in trips_per_person])

    # Impute activity duration
    df_duration = pd.DataFrame(df_trips[[
        "person_id", "trip_id", "arrival_time"
    ]], copy = True)

    df_following = pd.DataFrame(df_trips[[
        "person_id", "trip_id", "departure_time"
    ]], copy = True)
    df_following.columns = ["person_id", "trip_id", "following_trip_departure_time"]
    df_following["trip_id"] = df_following["trip_id"] - 1

    df_duration = pd.merge(df_duration, df_following, on = ["person_id", "trip_id"])
    df_duration["activity_duration"] = df_duration["following_trip_departure_time"] - df_duration["arrival_time"]
    df_duration.loc[df_duration["activity_duration"] < 0.0, "activity_duration"] += 24.0 * 3600.0

    df_duration = df_duration[["person_id", "trip_id", "activity_duration"]]
    df_trips = pd.merge(df_trips, df_duration, how = "left", on = ["person_id", "trip_id"])

    # Clean up
    df_trips = df_trips[[
        "person_id", "trip_id", "new_trip_id", "preceeding_purpose", "following_purpose", "mode",
        "departure_time", "arrival_time", "crowfly_distance", "activity_duration", "origin_x", "origin_y", "destination_x", "destination_y", "origin_zone", "destination_zone"
    ]]

    sameX = df_trips.index[df_trips["origin_x"] == df_trips["destination_x"]].tolist()
    sameX = df_trips.index.isin(sameX)
    sameY = df_trips.index[df_trips["origin_y"] == df_trips["destination_y"]].tolist() 
    sameY = df_trips.index.isin(sameX)
    same_loc = np.logical_and(sameX, sameY)
    df_trips[~same_loc]


    #### From here everything as Paris

    # Contains car
    df_cars = df_trips[df_trips["mode"] == "car"][["person_id"]].drop_duplicates()
    df_cars["has_car_trip"] = True
    df_persons = pd.merge(df_persons, df_cars, how = "left")
    df_persons["has_car_trip"] = df_persons["has_car_trip"].fillna(False)

    # Primary activity information
    df_education = df_trips[df_trips["following_purpose"] == "education"][["person_id"]].drop_duplicates()
    df_education["has_education_trip"] = True
    df_persons = pd.merge(df_persons, df_education, how = "left")
    df_persons["has_education_trip"] = df_persons["has_education_trip"].fillna(False)

    df_work = df_trips[df_trips["following_purpose"] == "work"][["person_id"]].drop_duplicates()
    df_work["has_work_trip"] = True
    df_persons = pd.merge(df_persons, df_work, how = "left")
    df_persons["has_work_trip"] = df_persons["has_work_trip"].fillna(False)

    # Find commute information
    df_commute = df_trips[df_trips["following_purpose"].isin(["work", "education"])]
    df_commute = df_commute.sort_values(by = ["person_id", "crowfly_distance"])
    df_commute = df_commute.drop_duplicates("person_id", keep = "last")

    df_commute = df_commute[["person_id", "crowfly_distance", "mode"]]
    df_commute.columns = ["person_id", "commute_distance", "commute_mode"]

    df_persons = pd.merge(df_persons, df_commute, on = "person_id", how = "left")

    assert(not df_persons[df_persons["has_work_trip"]]["commute_distance"].isna().any())
    assert(not df_persons[df_persons["has_education_trip"]]["commute_distance"].isna().any())

    # Passengers

    df_passenger = pd.DataFrame(df_trips[["person_id", "mode"]], copy = True)
    df_passenger = df_passenger[df_passenger["mode"] == "car_passenger"][["person_id"]]
    df_passenger = df_passenger.drop_duplicates()
    df_passenger["is_passenger"] = True

    df_persons = pd.merge(df_persons, df_passenger, on = "person_id", how = "left")
    df_persons["is_passenger"] = df_persons["is_passenger"].fillna(False)
    df_persons["is_passenger"] = df_persons["is_passenger"].astype(np.bool)

    #adapt employed variable
    #there are young persons that go to education, but are not classified as students
    #df_persons.loc[(df_persons["has_education_trip"]) & (df_persons["age"]<16), "employment"] = "student"
    return df_persons, df_trips
