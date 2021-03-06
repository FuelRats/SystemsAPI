def includeme(config):
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')
    config.add_route('search', '/search')
    config.add_route('typeahead', '/typeahead')
    config.add_route('mecha', '/mecha')
    config.add_route('landmark', '/landmark')
    config.add_route('galaxy', '/galaxy')
    config.add_route('procname', '/procname')
    config.add_route('nearest_populated', '/nearest_populated')
    config.add_route('nearest_scoopable', '/nearest_scoopable')
    config.add_route('heatmap', '/heatmap')
