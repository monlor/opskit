package logger

import (
	"fmt"
	"os"
	"time"

	"github.com/fatih/color"
)

var (
	debugEnabled = false
	
	// Color functions
	colorInfo    = color.New(color.FgBlue).SprintFunc()
	colorSuccess = color.New(color.FgGreen).SprintFunc()
	colorWarning = color.New(color.FgYellow).SprintFunc()
	colorError   = color.New(color.FgRed).SprintFunc()
	colorDebug   = color.New(color.FgCyan).SprintFunc()
)

// Init initializes the logger
func Init() {
	if os.Getenv("OPSKIT_DEBUG") == "1" {
		debugEnabled = true
	}
}

// timestamp returns formatted timestamp
func timestamp() string {
	return time.Now().Format("2006-01-02 15:04:05")
}

// Info logs an info message
func Info(format string, args ...interface{}) {
	message := fmt.Sprintf(format, args...)
	fmt.Printf("[%s] %s %s\n", timestamp(), colorInfo("INFO"), message)
}

// Success logs a success message
func Success(format string, args ...interface{}) {
	message := fmt.Sprintf(format, args...)
	fmt.Printf("[%s] %s %s\n", timestamp(), colorSuccess("SUCCESS"), message)
}

// Warning logs a warning message
func Warning(format string, args ...interface{}) {
	message := fmt.Sprintf(format, args...)
	fmt.Printf("[%s] %s %s\n", timestamp(), colorWarning("WARNING"), message)
}

// Error logs an error message
func Error(format string, args ...interface{}) {
	message := fmt.Sprintf(format, args...)
	fmt.Fprintf(os.Stderr, "[%s] %s %s\n", timestamp(), colorError("ERROR"), message)
}

// Debug logs a debug message (only if debug is enabled)
func Debug(format string, args ...interface{}) {
	if debugEnabled {
		message := fmt.Sprintf(format, args...)
		fmt.Printf("[%s] %s %s\n", timestamp(), colorDebug("DEBUG"), message)
	}
}

// Fatal logs an error message and exits
func Fatal(format string, args ...interface{}) {
	Error(format, args...)
	os.Exit(1)
}