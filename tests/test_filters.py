from hydrodashboards import bokeh

# %% here we overwrite the default (WAM) config with WIK
AAM_CONFIG_JSON = r"data\wik_config.json"
bokeh.set_config_json(AAM_CONFIG_JSON)
#bokeh.delete_cache()

# %% now we import main (will be initialized for WIK)
from hydrodashboards.bokeh.main import (config,
    filters, 
    data, 
    locations, 
    CONFIG_JSON, 
    parameters,
    search_period,
    start_time_series_loader,
    update_time_series_view,
    time_figure_layout,
    time_figure_widget
    
    )

#%%
#Test: Selecteer eerst parameter: Neerslag, dan 't Heufke, daarna filter oppervlaktewater. Nu kun je parameters van opp water ook aanklikken.  
#    "filters: ['WIK_KET_Neerslag', 'Hydronet_Kwartier']", "locations: ['OSS-HAR-HEU']", "parameters: ['Q.afgeleid', 'Q.meting', 'K.meting', 'H.meting']"

filters[0].active = [0]
locations.active = [1]
parameters.active = [0]
print(locations.active,parameters.active)
filters[1].active = [0]
parameters.active = [0,1,2]
search_period.children[0].value = "2014-01-01"
start_time_series_loader()
update_time_series_view()
