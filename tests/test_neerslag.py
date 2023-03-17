from hydrodashboards import bokeh

# %% here we overwrite the default (WAM) config with WIK
AAM_CONFIG_JSON = r"data\wik_config.json"
bokeh.set_config_json(AAM_CONFIG_JSON)
bokeh.delete_cache()

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
    time_figure_widget,
    y_labels
    
    )

#%%

# Y-as figuur op -800 mm 
filters[0].active = [0]
print("0",filters[0].labels)  
locations.active = [0,1]
print(locations.active)
parameters.active = [0]
search_period.children[0].value = "2014-01-01"
start_time_series_loader()
update_time_series_view()
print(y_labels)
# hoe vraag ik de y-as op?




#['WIK_KET_Neerslag', 'Hydronet_Kwartier']", "locations: ['105VLW', '227DB', '232C', 'ADCP105VLW', 'UDE-UDE-RAA']", "parameters: ['Q.meting', 'K.meting', 'H.meting', 'P.radar.cal * early', 'KW.signaal * Signal_Noise_Ratio', 'H.streef', 'V.meting']
#Before legend properties can be set, you must add a Legend explicitly, or call a glyph method with a legend parameter set.

