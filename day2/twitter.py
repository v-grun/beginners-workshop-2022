import dlt
import requests


@dlt.source
def twitter_source(search_terms, api_secret_key=dlt.secrets.value, start_time=None, end_time=None):
    return twitter_search(search_terms, start_time=start_time, end_time=end_time, api_secret_key=api_secret_key)


def _create_auth_headers(api_secret_key):
    """Constructs Bearer type authorization header which is the most common authorization method"""
    headers = {
        "Authorization": f"Bearer {api_secret_key}"
    }
    return headers


def _paginated_get(url, headers, params, max_pages=5):
    """Requests and yields up to `max_pages` pages of results as per Twitter API docs: https://developer.twitter.com/en/docs/twitter-api/pagination"""
    while True:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        page = response.json()
        # show the pagination info
        meta = page["meta"]
        print(meta)

        yield page

        # get next page token
        next_token = meta.get('next_token')
        max_pages -= 1

        # if no more pages or we are at the maximum
        if not next_token or max_pages == 0:
            break
        else:
            # set the next_token parameter to get next page
            params['pagination_token'] = next_token


@dlt.resource(write_disposition="append")
def twitter_search(search_terms, start_time=None, end_time=None, api_secret_key=dlt.secrets.value):

    headers = _create_auth_headers(api_secret_key)
    # get search results for each term
    for search_term in search_terms:
        params = {
            'query': search_term,
            'max_results': 20,  # maximum elements per page: we set it to low value to demonstrate the paginator
            'start_time': start_time,  # '2022-11-08T00:00:00.000Z',
            'end_time': end_time,  # '2022-11-09T00:00:00.000Z',
            'expansions': 'author_id',
            'tweet.fields': 'context_annotations,id,text,author_id,in_reply_to_user_id,geo,conversation_id,created_at,lang,public_metrics,referenced_tweets,reply_settings,source',
            'user.fields': 'id,name,username,created_at,description,public_metrics,verified'
            }

    url = "https://api.twitter.com/2/tweets/search/recent"
    # make request
    response = _paginated_get(url, headers=headers, params=params)
    for page in response:
        page['search_term'] = search_term
        yield page


if __name__=='__main__':

    search_terms = ['python data engineer']
    dataset_name ='tweets'

    # search last day
    from datetime import datetime, timedelta, timezone
    
    last_midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) 
    data_interval_start = last_midnight - timedelta(days=1)
    data_interval_end = last_midnight

    start_time = data_interval_start.isoformat()
    end_time = data_interval_end.isoformat()

    pipeline = dlt.pipeline(pipeline_name='twitter', destination='bigquery', dataset_name='twitter_data')

    # run the pipeline with your parameters and print the outcome
    load_info = pipeline.run(twitter_source(search_terms=search_terms, start_time=start_time, end_time=end_time))

    print(load_info)
