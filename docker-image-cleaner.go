package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/docker/docker/api/types"
	"github.com/docker/docker/client"
	"log"
)

type logger interface {
	logDebug(msg string)
	log(msg string)
	setDebug(flag bool)
	setQuiet(flag bool)
}

type cliLog struct {
	debug bool
	quiet bool
}

func (c *cliLog) logDebug(msg string) {
	if c.debug {
		log.Printf("DEBUG: %s", msg)
	}
}

func (c *cliLog) log(msg string) {
	if !c.quiet {
		log.Printf("INFO: %s", msg)
	}
}

func (c *cliLog) setDebug(flag bool) {
	c.debug = flag
}

func (c *cliLog) setQuiet(flag bool) {
	c.quiet = flag
}

// ImageGroup represents an image with its tags grouped by shared ID
type ImageGroup struct {
	ID       string
	RepoTags []string
	Created  time.Time
	Size     int64
	ParentID string
}

// ImageRepository groups images by repository name (before colon)
type ImageRepository struct {
	Name   string
	Images []ImageGroup
}

// Config holds all configuration options for the cleaner
type Config struct {
	Noop           bool // Dry run mode
	Force          bool // Force delete images used by containers
	Verbose        bool // Print verbose output
	ImagesToKeep   int  // Number of images to keep per repository
	KeepNoneImages bool // Keep <none> dangling images
	DockerClient   *client.Client
	Logger         logger
	APITimeout     time.Duration // Timeout for Docker API calls
}

const defaultAPITimeout = 60 * time.Second

func getRepoName(repoTag string) string {
	parts := strings.SplitN(repoTag, ":", 2)
	if len(parts) < 2 {
		return "<none>"
	}
	return parts[0]
}

func listImages(ctx context.Context, l logger, dockerCli *client.Client) ([]types.ImageSummary, error) {
	l.log("Listing all Docker images")
	images, err := dockerCli.ImageList(ctx, types.ImageListOptions{All: true})
	if err != nil {
		l.log(fmt.Sprintf("Error listing images: %v", err))
		return nil, err
	}
	l.log(fmt.Sprintf("Found %d images", len(images)))
	return images, nil
}

func groupImagesByRepo(images []types.ImageSummary) map[string][]ImageGroup {
	// Map: repo name -> list of ImageGroup
	repos := make(map[string][]ImageGroup)
	// Map: image ID -> ImageGroup (to handle multi-tag images)
	imageMap := make(map[string]*ImageGroup)

	for _, img := range images {
		// Skip images without RepoTags or with <none>:<none>
		if len(img.RepoTags) == 0 {
			// Dangling image (<none>:<none>)
			repoName := "<none>"
			ig := &ImageGroup{
				ID:       img.ID,
				RepoTags: img.RepoTags,
				Created:  time.Unix(img.Created, 0),
				Size:     img.Size,
				ParentID: img.ParentID,
			}
			imageMap[img.ID] = ig
			repos[repoName] = append(repos[repoName], *ig)
			continue
		}

		// Get or create ImageGroup for this image ID (all tags belong to same image)
		ig, exists := imageMap[img.ID]
		if !exists {
			ig = &ImageGroup{
				ID:       img.ID,
				RepoTags: []string{},
				Created:  time.Unix(img.Created, 0),
				Size:     img.Size,
				ParentID: img.ParentID,
			}
			imageMap[img.ID] = ig
		}

		// Add all tags from this image to the ImageGroup
		for _, repoTag := range img.RepoTags {
			hasTag := false
			for _, t := range ig.RepoTags {
				if t == repoTag {
					hasTag = true
					break
				}
			}
			if !hasTag {
				ig.RepoTags = append(ig.RepoTags, repoTag)
			}
		}

		// Add to repo (deduplicated by image ID)
		repoName := getRepoName(img.RepoTags[0])
		addToRepo := true
		for _, existing := range repos[repoName] {
			if existing.ID == img.ID {
				addToRepo = false
				break
			}
		}
		if addToRepo {
			repos[repoName] = append(repos[repoName], *ig)
		}
	}

	return repos
}

func sortImagesInRepos(repos map[string][]ImageGroup) {
	for repoName, images := range repos {
		// Sort by Created descending (newest first)
		for i := 0; i < len(images); i++ {
			for j := i + 1; j < len(images); j++ {
				if images[j].Created.After(images[i].Created) {
					images[i], images[j] = images[j], images[i]
				}
			}
		}
		repos[repoName] = images
	}
}

func getImagesToDelete(repos map[string][]ImageGroup, imagesToKeep int, keepNoneImages bool) []ImageGroup {
	var toDelete []ImageGroup

	for repoName, images := range repos {
		if repoName == "<none>" {
			if keepNoneImages {
				continue
			}
			// Keep only imagesToKeep from <none> repo
			if len(images) > imagesToKeep {
				toDelete = append(toDelete, images[imagesToKeep:]...)
			}
			continue
		}

		// Keep only imagesToKeep per repo
		if len(images) > imagesToKeep {
			toDelete = append(toDelete, images[imagesToKeep:]...)
		}
	}

	return toDelete
}

func removeImageTag(ctx context.Context, l logger, dockerCli *client.Client, tag string, force bool) error {
	l.logDebug(fmt.Sprintf("Removing tag: %s", tag))
	_, err := dockerCli.ImageRemove(ctx, tag, types.ImageRemoveOptions{
		Force: force,
	})
	if err != nil {
		return err
	}
	return nil
}

func deleteImageGroup(ctx context.Context, l logger, noop bool, force bool, dockerCli *client.Client, img ImageGroup) error {
	if noop {
		l.log(fmt.Sprintf("Would delete image %s: %v", img.ID, img.RepoTags))
		return nil
	}

	l.log(fmt.Sprintf("Deleting image %s: %v", img.ID, img.RepoTags))

	// Delete each tag one by one. When the last tag is removed,
	// Docker will automatically delete the image itself.
	for _, tag := range img.RepoTags {
		err := removeImageTag(ctx, l, dockerCli, tag, false)
		if err != nil {
			// Continue with other tags even if one fails
			l.logDebug(fmt.Sprintf("Error removing tag %s: %v (continuing with other tags)", tag, err))
		}
	}

	return nil
}

func deleteImages(ctx context.Context, l logger, noop bool, force bool, dockerCli *client.Client, images []ImageGroup) (int, int) {
	success := 0
	failed := 0

	for _, img := range images {
		err := deleteImageGroup(ctx, l, noop, force, dockerCli, img)
		if err != nil {
			failed++
		} else {
			success++
		}
	}

	return success, failed
}

func processImages(cfg Config) {
	l := cfg.Logger
	dockerCli := cfg.DockerClient

	// Create context with timeout for Docker API calls
	ctx, cancel := context.WithTimeout(context.Background(), cfg.APITimeout)
	defer cancel()

	images, err := listImages(ctx, l, dockerCli)
	if err != nil {
		l.log(fmt.Sprintf("Error getting images: %v", err))
		return
	}

	l.logDebug(fmt.Sprintf("Processing %d images", len(images)))

	repos := groupImagesByRepo(images)
	l.logDebug(fmt.Sprintf("Found %d repositories", len(repos)))

	// Sort images in repos by creation date (newest first)
	sortImagesInRepos(repos)

	// Sort and get images to delete
	toDelete := getImagesToDelete(repos, cfg.ImagesToKeep, cfg.KeepNoneImages)
	l.log(fmt.Sprintf("Images to delete: %d", len(toDelete)))

	if len(toDelete) == 0 {
		l.log("No images to delete")
		return
	}

	// Log verbose info
	if cfg.Verbose {
		for _, img := range toDelete {
			l.log(fmt.Sprintf("  - %s tags=%v (created: %s)", img.ID, img.RepoTags, img.Created.Format(time.RFC3339)))
		}
	}

	success, failed := deleteImages(ctx, l, cfg.Noop, cfg.Force, dockerCli, toDelete)

	if cfg.Noop {
		l.log(fmt.Sprintf("Dry run complete: would delete %d images", len(toDelete)))
	} else {
		l.log(fmt.Sprintf("Deletion complete: %d successful, %d failed", success, failed))
	}
}

func main() {
	const (
		debugFlagHelp         = "Debug mode"
		quietFlagHelp         = "Don't show standard messages"
		noopFlagHelp          = "Dry run (no actual changes)"
		verboseFlagHelp       = "Print verbose output"
		oneshotFlagHelp       = "Run once and exit (daemon mode by default)"
		sleepDurationFlagHelp = "Time to sleep between runs"
		imagesToKeepFlagHelp  = "Number of images to keep per repository"
		keepNoneFlagHelp      = "Keep <none> dangling images"
		forceFlagHelp         = "Force delete (for images used by containers)"
	)

	const (
		defaultSleepDurationString = "5m"
		defaultImagesToKeep        = 2
	)

	defaultSleepDuration, _ := time.ParseDuration(defaultSleepDurationString)

	var debug bool
	var quiet bool
	var noop bool
	var verbose bool
	var oneshot bool
	var keepNone bool
	var force bool
	var imagesToKeep int
	var sleepDuration time.Duration

	flag.BoolVar(&debug, "d", false, debugFlagHelp)
	flag.BoolVar(&quiet, "q", false, quietFlagHelp)
	flag.BoolVar(&noop, "noop", false, noopFlagHelp)
	flag.BoolVar(&verbose, "v", false, verboseFlagHelp)
	flag.BoolVar(&oneshot, "oneshot", false, oneshotFlagHelp)
	flag.BoolVar(&keepNone, "keep-none-images", false, keepNoneFlagHelp)
	flag.BoolVar(&force, "f", false, forceFlagHelp)
	flag.IntVar(&imagesToKeep, "images-to-keep", defaultImagesToKeep, imagesToKeepFlagHelp)
	flag.DurationVar(&sleepDuration, "sleepDuration", defaultSleepDuration, sleepDurationFlagHelp)
	flag.Parse()

	// Validate sleepDuration (must be > 0 for daemon mode)
	if sleepDuration <= 0 {
		log.Fatal("ERROR: sleepDuration must be greater than 0")
	}

	if imagesToKeep < 0 {
		log.Fatal("ERROR: images-to-keep must be >= 0")
	}

	l := new(cliLog)
	l.setQuiet(quiet)
	l.setDebug(debug)

	dockerCli, err := client.NewClientWithOpts(client.FromEnv)
	if err != nil {
		log.Panicf("Error creating Docker client: %s", err)
	}
	defer dockerCli.Close()

	l.log("Docker Image Cleaner started")

	// Create Config struct
	cfg := Config{
		Noop:           noop,
		Force:          force,
		Verbose:        verbose,
		ImagesToKeep:   imagesToKeep,
		KeepNoneImages: keepNone,
		DockerClient:   dockerCli,
		Logger:         l,
		APITimeout:     defaultAPITimeout,
	}

	// Set up signal handling for graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	for {
		select {
		case <-sigChan:
			l.log("Received shutdown signal - exiting gracefully")
			return
		default:
			processImages(cfg)

			if oneshot {
				l.log("Oneshot mode - exiting")
				return
			}

			l.log(fmt.Sprintf("Sleeping for %s", sleepDuration))

			// Non-blocking sleep with ability to check signals
			select {
			case <-sigChan:
				l.log("Received shutdown signal during sleep - exiting gracefully")
				return
			case <-time.After(sleepDuration):
				// Continue to next iteration
			}
		}
	}
}
