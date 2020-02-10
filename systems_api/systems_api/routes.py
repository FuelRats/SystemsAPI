def includeme(config):
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')
    config.add_route('search', '/search')
    config.add_route('typeahead', '/typeahead')
    config.add_route('mecha', '/mecha')
    config.add_route('landmark', '/landmark')
