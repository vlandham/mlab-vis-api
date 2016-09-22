# -*- coding: utf-8 -*-
'''
Data class for accessing data for API calls.
'''
from gcloud.bigtable.row_filters import FamilyNameRegexFilter
from mlab_api.data.base_data import Data
from mlab_api.constants import TABLE_KEYS
from mlab_api.data.table_config import get_table_config
import mlab_api.data.data_utils as du
import mlab_api.data.bigtable_utils as bt
from mlab_api.stats import statsd

class LocationData(Data):
    '''
    Connect to BigTable and pull down data.
    '''

    def get_location_info(self, location_id):
        '''
        Get info about specific location
        '''

        table_config = get_table_config(self.table_configs,
                                        None,
                                        du.list_table('locations'))
        # add empty field to get child location in there
        location_key_fields = du.get_key_fields(["info", location_id], table_config)

        row_key = du.BIGTABLE_KEY_DELIM.join(location_key_fields)
        row = ""
        with statsd.timer('location.info.get_row'):
            row = bt.get_row(table_config, self.get_pool(), row_key)
        row["meta"]["id"] = location_id

        return row

    def get_location_children(self, location_id, type_filter=None):
        '''
        Return information about children regions of a location
        '''
        table_config = get_table_config(self.table_configs,
                                        None,
                                        du.list_table('locations'))
        location_key_fields = du.get_location_key_fields(location_id, table_config)

        location_key_field = du.BIGTABLE_KEY_DELIM.join(location_key_fields)

        results = []
        with statsd.timer('locations.children.scan_table'):
            results = bt.scan_table(table_config, self.get_pool(), prefix=location_key_field)
            if type_filter:
                results = [r for r in results if r['meta']['type'] == type_filter]

        return {"results": results}

    def get_location_metrics(self, location_id, time_aggregation, starttime, endtime):
        '''
        Get data for specific location at a specific
        frequency between start and stop times.
        '''

        table_config = get_table_config(self.table_configs,
                                        time_aggregation,

                                        TABLE_KEYS["locations"])


        # expect start and end to be inclusive
        inclusive_endtime = du.add_time(endtime, 1, time_aggregation)
        location_key_fields = du.get_location_key_fields(location_id, table_config)

        starttime_fields = du.get_time_key_fields(starttime, time_aggregation, table_config)
        endtime_fields = du.get_time_key_fields(inclusive_endtime, time_aggregation, table_config)

        start_key = du.BIGTABLE_KEY_DELIM.join(location_key_fields + starttime_fields)
        end_key = du.BIGTABLE_KEY_DELIM.join(location_key_fields + endtime_fields)

        # BIGTABLE QUERY
        results = []
        with statsd.timer('locations.metrics.scan_table'):
            results = bt.scan_table(table_config, self.get_pool(), start_key=start_key, end_key=end_key)

        formatted = {}

        with statsd.timer('locations.metrics.format_data'):
            formatted = du.format_metric_data(results, starttime=starttime, endtime=endtime, agg=time_aggregation)

        # set the ID to be the location ID
        formatted["meta"]["id"] = location_id

        return formatted

    def get_location_client_isps(self, location_id, include_data):
        '''
        Get list and info of client isps for a location
        '''

        # config_id = TABLE_KEYS["CLIENT_LOCATION_KEY"] + '_' + TABLE_KEYS["CLIENT_ASN_KEY"] + '_list'

        config_id = du.list_table('clients', 'locations')

        table_config = get_table_config(self.table_configs, None, config_id)

        location_key_fields = du.get_location_key_fields(location_id, table_config)

        location_key_field = du.BIGTABLE_KEY_DELIM.join(location_key_fields)

        params = {"prefix":location_key_field}
        if not include_data:
            params["filter"] = FamilyNameRegexFilter('meta')

        results = []
        with statsd.timer('locations.clientisps_list.scan_table'):
            results = bt.scan_table(table_config, self.get_pool(), **params)

        sorted_results = []
        with statsd.timer('locations.clientisps_list.sort_results'):
            # NOTE: in this bigtable - 'last_year_test_count' is in `meta` - not `data`.
            sorted_results = sorted(results, key=lambda k: k['meta']['last_year_test_count'], reverse=True)
        return {"results": sorted_results}

    def get_location_client_isp_info(self, location_id, client_isp_id):
        '''
        Get static information about
        '''

        # config_id = TABLE_KEYS["CLIENT_LOCATION_KEY"] + '_' + TABLE_KEYS["CLIENT_ASN_KEY"] + '_list'
        config_id = du.list_table('clients', 'locations')
        table_config = get_table_config(self.table_configs, None, config_id)

        key_fields = du.get_key_fields([location_id, client_isp_id], table_config)

        row_key = du.BIGTABLE_KEY_DELIM.join(key_fields)

        results = []
        with statsd.timer('locations.clientisps_info.scan_table'):
            results = bt.get_row(table_config, self.get_pool(), row_key)
        results["meta"]["id"] = client_isp_id
        return results



    def get_location_client_isp_metrics(self, location_id, client_isp_id,
                                        time_aggregation, starttime, endtime):
        '''
        Get data for specific location at a specific
        frequency between start and stop times for a
        specific client ISP.
        '''
        # Create Row Key
        agg_name = TABLE_KEYS["clients"] + '_' + TABLE_KEYS["locations"]

        table_config = get_table_config(self.table_configs,
                                        time_aggregation,
                                        agg_name)

        key_fields = du.get_key_fields([client_isp_id, location_id], table_config)

        starttime_fields = du.get_time_key_fields(starttime, time_aggregation, table_config)

        inclusive_endtime = du.add_time(endtime, 1, time_aggregation)
        endtime_fields = du.get_time_key_fields(inclusive_endtime, time_aggregation, table_config)

        # Start and End -- Row Keys
        start_key = du.BIGTABLE_KEY_DELIM.join(key_fields + starttime_fields)

        end_key = du.BIGTABLE_KEY_DELIM.join(key_fields + endtime_fields)

        # Prepare to query the table

        results = []
        with statsd.timer('locations.clientisps_metrics.scan_table'):
            results = bt.scan_table(table_config, self.get_pool(), start_key=start_key, end_key=end_key)

        formatted = {}

        with statsd.timer('locations.clientisps_metrics.format_data'):
            # format output for API
            formatted = du.format_metric_data(results, starttime=starttime, endtime=endtime, agg=time_aggregation)

        # set the ID to be the Client ISP ID
        formatted["meta"]["id"] = client_isp_id

        return formatted

    def get_location_search(self, location_query):
        '''
        API for location search
        '''
        table_config = get_table_config(self.table_configs,
                                        None,
                                        du.search_table('locations'))


        results = []
        with statsd.timer('locations.search.scan_table'):
            results = bt.scan_table(table_config, self.get_pool(), prefix=location_query)

        sorted_results = []
        with statsd.timer('locations.search.sort_results'):
            # sort based on test_count
            sorted_results = sorted(results, key=lambda k: k['data']['test_count'], reverse=True)
        return {"results": sorted_results}
