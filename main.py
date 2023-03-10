import toml
from uoc import UOC

# get variables from file toml (config.toml)
file_config = "config.toml"
with open(file_config, 'r', encoding='UTF-8') as f:
    config = toml.load(f)

# create object uoc
uoc = UOC(config)

if not uoc.error:
    # login
    uoc.login_UOC()
    if uoc.campusSessionId != "" and not uoc.error:
        # create timeline html to show
        uoc.get_timeline_html(sorted_by="days", create_csv=True)
        # view messages
        uoc.get_messages()

if uoc.error:
    print(uoc.errorMessage)

