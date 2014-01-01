package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"runtime"
	"time"
)

func main() {
	type MyReport struct {
		Hostname   string `json:"hostname"`
		Date       string `json:"date"`
		ReportType string `json:"type"`
		GoVersion  string `json:"go_version"`
	}

	now := time.Now().UTC()
	hostname, _ := os.Hostname()
	rep1 := MyReport{
		hostname,
		now.Format("2006-01-02 15:04:05.") + fmt.Sprintf("%d", (now.Nanosecond()/1e3)),
		"hello_from_go",
		runtime.Version(),
	}

	b, _ := json.Marshal(rep1)
	_, err := http.Post("http://localhost:8888/report", "application/json", bytes.NewBuffer(b))

	if err != nil {
		fmt.Println("Could not send request:", err)
		return
	}
}
