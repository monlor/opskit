package downloader

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"

	"opskit/internal/config"
	"opskit/internal/logger"
	"github.com/schollz/progressbar/v3"
)

// Downloader handles file downloads
type Downloader struct {
	config *config.Config
}

// NewDownloader creates a new downloader
func NewDownloader(cfg *config.Config) *Downloader {
	return &Downloader{config: cfg}
}

// DownloadFile downloads a file from URL to local path
func (d *Downloader) DownloadFile(url, outputPath string) error {
	logger.Debug("Downloading %s to %s", url, outputPath)
	
	// Create directory if it doesn't exist
	if err := os.MkdirAll(filepath.Dir(outputPath), 0755); err != nil {
		return fmt.Errorf("failed to create directory: %w", err)
	}
	
	// Create the file
	out, err := os.Create(outputPath)
	if err != nil {
		return fmt.Errorf("failed to create file: %w", err)
	}
	defer out.Close()
	
	// Get the data
	resp, err := http.Get(url)
	if err != nil {
		return fmt.Errorf("failed to download file: %w", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("bad status: %s", resp.Status)
	}
	
	// Create progress bar
	bar := progressbar.DefaultBytes(
		resp.ContentLength,
		fmt.Sprintf("Downloading %s", filepath.Base(outputPath)),
	)
	
	// Write the body to file with progress
	_, err = io.Copy(io.MultiWriter(out, bar), resp.Body)
	if err != nil {
		return fmt.Errorf("failed to write file: %w", err)
	}
	
	logger.Success("Downloaded %s", filepath.Base(outputPath))
	return nil
}

// LoadOrDownloadConfig loads config from local or downloads if needed
func (d *Downloader) LoadOrDownloadConfig(filename string) (string, error) {
	// Check local file first (development mode)
	localPath := filepath.Join("tools", filename)
	if _, err := os.Stat(localPath); err == nil {
		logger.Debug("Using local file: %s", localPath)
		return localPath, nil
	}
	
	// Check cache
	cachePath := filepath.Join(d.config.ToolsDir(), filename)
	if !d.config.ShouldUpdate(cachePath) {
		logger.Debug("Using cached file: %s", cachePath)
		return cachePath, nil
	}
	
	// Download from remote
	url := fmt.Sprintf("%s/tools/%s", d.config.GithubRepo, filename)
	if err := d.DownloadFile(url, cachePath); err != nil {
		// If download fails and cached file exists, use cached version
		if _, statErr := os.Stat(cachePath); statErr == nil {
			logger.Warning("Download failed, using cached version: %s", err)
			return cachePath, nil
		}
		return "", fmt.Errorf("failed to download and no cached version available: %w", err)
	}
	
	return cachePath, nil
}

// LoadOrDownloadTool loads tool from local or downloads if needed
func (d *Downloader) LoadOrDownloadTool(filename string) (string, error) {
	// Check local file first (development mode)
	localPath := filepath.Join("tools", filename)
	if _, err := os.Stat(localPath); err == nil {
		logger.Debug("Using local tool: %s", localPath)
		return localPath, nil
	}
	
	// Check cache
	cachePath := filepath.Join(d.config.ToolsDir(), filename)
	if !d.config.ShouldUpdate(cachePath) {
		logger.Debug("Using cached tool: %s", cachePath)
		return cachePath, nil
	}
	
	// Download from remote
	url := fmt.Sprintf("%s/tools/%s", d.config.GithubRepo, filename)
	if err := d.DownloadFile(url, cachePath); err != nil {
		// If download fails and cached file exists, use cached version
		if _, statErr := os.Stat(cachePath); statErr == nil {
			logger.Warning("Download failed, using cached version: %s", err)
			return cachePath, nil
		}
		return "", fmt.Errorf("failed to download and no cached version available: %w", err)
	}
	
	// Make tool executable
	if err := os.Chmod(cachePath, 0755); err != nil {
		logger.Warning("Failed to make tool executable: %v", err)
	}
	
	return cachePath, nil
}