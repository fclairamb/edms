#ifdef SHELL
gcc $0 -Wall -Werror -ljson -lcurl && ./a.out && rm a.out && exit 0
#endif

#include <stdio.h>
#include <memory.h>
#include <unistd.h>
#include <stdlib.h>
#include <json-c/json.h>
#include <curl/curl.h>

int main() {
	json_object * report = json_object_new_object();
	{ // We prepare the report object

		{ // Hostname
			char buffer[64];
			gethostname(buffer, sizeof(buffer));
			json_object_object_add(report, "hostname", json_object_new_string(buffer));
		}
		
		{ // Date
			char buffer[64];
			struct timeval tv;
			struct tm *tm;

			gettimeofday(&tv, NULL);
			if ((tm = gmtime(&tv.tv_sec)) != NULL) {
				char fmt[64];
				strftime(fmt, sizeof (fmt), "%Y-%m-%d %H:%M:%S.%%06u", tm);
				snprintf(buffer, sizeof (buffer), fmt, tv.tv_usec);
			}

			json_object_object_add(report, "date", json_object_new_string(buffer));
		}

		// Type
		json_object_object_add( report, "type", json_object_new_string("hello_from_c"));

		{ // Load
			double load;
			getloadavg( & load, 1 );
			json_object_object_add( report, "loadavg", json_object_new_double(load));
		}
	}

	// We convert the report to a json string
	const char * json = json_object_to_json_string(report);

	CURLcode res;
	{ // We send the request
		CURL * curl = curl_easy_init();
		curl_easy_setopt(curl, CURLOPT_URL, "http://localhost:8888/report");
		curl_easy_setopt(curl, CURLOPT_POST, 1L);
		curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json); 
		curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, strlen(json)); 

		res = curl_easy_perform(curl);

		curl_easy_cleanup(curl);
	}

	return res;
}
