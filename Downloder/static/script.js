const button = document.getElementById("downloadBtn");
const input = document.getElementById("videoUrl");
const message = document.getElementById("message");

const resultCard = document.getElementById("resultCard");
const platformName = document.getElementById("platformName");
const downloadVideoBtn = document.getElementById("downloadVideoBtn");
const qualitySelect = document.getElementById("quality");


// ==========================================
// MAIN BUTTON
// ==========================================

if (button) {
    button.addEventListener("click", checkUrl);
}


// ==========================================
// ENTER KEY
// ==========================================

if (input) {
    input.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
            checkUrl();
        }
    });
}


// ==========================================
// CHECK URL
// ==========================================

async function checkUrl() {

    if (!input || !button || !message || !resultCard) {
        return;
    }

    const url = input.value.trim();


    // ======================================
    // EMPTY URL
    // ======================================

    if (!url) {
        showMessage("Please paste a video URL.");
        resultCard.style.display = "none";
        return;
    }


    // ======================================
    // URL VALIDATION
    // ======================================

    let parsedUrl;

    try {
        parsedUrl = new URL(url);
    }

    catch (error) {
        showMessage("Please enter a valid URL.");
        resultCard.style.display = "none";
        return;
    }


    // ======================================
    // HTTP / HTTPS ONLY
    // ======================================

    if (
        parsedUrl.protocol !== "http:" &&
        parsedUrl.protocol !== "https:"
    ) {
        showMessage("Please enter an HTTP or HTTPS URL.");
        resultCard.style.display = "none";
        return;
    }


    // ======================================
    // LOADING START
    // ======================================

    button.disabled = true;
    button.classList.add("loading");
    button.textContent = "Checking...";

    message.textContent = "";
    resultCard.style.display = "none";


    // ======================================
    // API REQUEST
    // ======================================

    try {

        const response = await fetch(
            "/api/check-url",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    url: url
                })
            }
        );


        let data = {};

        try {
            data = await response.json();
        }

        catch (jsonError) {
            data = {};
        }


        // ==================================
        // SUCCESS
        // ==================================

        if (response.ok && data.success) {

            showMessage(
                "✓ " + (
                    data.message ||
                    "URL checked successfully."
                )
            );


            showResult(
                data.platform,
                data.video,
                url
            );

        }


        // ==================================
        // ERROR
        // ==================================

        else {

            showMessage(
                "✕ " +
                (
                    data.message ||
                    "Unable to process URL."
                )
            );

            resultCard.style.display = "none";
        }

    }


    // ======================================
    // NETWORK ERROR
    // ======================================

    catch (error) {

        console.error(error);

        showMessage(
            "Something went wrong. Please try again."
        );

        resultCard.style.display = "none";
    }


    // ======================================
    // LOADING END
    // ======================================

    finally {

        button.disabled = false;

        button.classList.remove("loading");

        button.textContent = "Check Link";
    }

}


// ==========================================
// SHOW MESSAGE
// ==========================================

function showMessage(text) {

    if (!message) {
        return;
    }

    message.textContent = text;
}


// ==========================================
// SHOW RESULT
// ==========================================

function showResult(platform, video, url) {

    if (!resultCard) {
        return;
    }


    resultCard.style.display = "flex";


    // ======================================
    // SAVE SOURCE URL
    // ======================================

    resultCard.dataset.sourceUrl = url;


    // ======================================
    // PLATFORM NAME
    // ======================================

    if (platformName) {

        const safePlatform =
            platform || "video";


        const formattedPlatform =
            safePlatform.charAt(0).toUpperCase() +
            safePlatform.slice(1);


        platformName.textContent =
            formattedPlatform + " URL detected";
    }


    // ======================================
    // VIDEO INFORMATION
    // ======================================

    if (video) {

        updateVideoInfo({

            title:
                video.title ||
                "Video",

            duration:
                video.duration ||
                "Unknown duration",

            thumbnail:
                video.thumbnail ||
                null

        });

    }

    else {

        updateVideoInfo({

            title:
                "Your video is ready",

            duration:
                "Available after processing",

            thumbnail:
                null

        });

    }

}


// ==========================================
// UPDATE VIDEO INFORMATION
// ==========================================

function updateVideoInfo(video) {

    const titleElement =
        document.getElementById("videoTitle");

    const durationElement =
        document.getElementById("videoDuration");

    const thumbnailElement =
        document.getElementById("videoThumbnail");

    const placeholderElement =
        document.querySelector(
            ".thumbnail-placeholder"
        );


    // ======================================
    // TITLE
    // ======================================

    if (titleElement) {

        titleElement.textContent =
            video.title || "Video";
    }


    // ======================================
    // DURATION
    // ======================================

    if (durationElement) {

        durationElement.textContent =
            video.duration || "";
    }


    // ======================================
    // THUMBNAIL
    // ======================================

    if (thumbnailElement) {

        if (video.thumbnail) {

            thumbnailElement.src =
                video.thumbnail;


            thumbnailElement.style.display =
                "block";


            if (placeholderElement) {

                placeholderElement.style.display =
                    "none";
            }

        }

        else {

            thumbnailElement.removeAttribute(
                "src"
            );


            thumbnailElement.style.display =
                "none";


            if (placeholderElement) {

                placeholderElement.style.display =
                    "flex";
            }

        }

    }

}


// ==========================================
// DOWNLOAD VIDEO BUTTON
// ==========================================

if (downloadVideoBtn) {

    downloadVideoBtn.addEventListener(
        "click",
        requestDownload
    );

}


// ==========================================
// DOWNLOAD REQUEST
// ==========================================

async function requestDownload() {

    if (!resultCard || !downloadVideoBtn) {
        return;
    }


    // ======================================
    // SOURCE URL
    // ======================================

    const sourceUrl =
        resultCard.dataset.sourceUrl;


    // ======================================
    // QUALITY
    // ======================================

    const quality =
        qualitySelect
            ? qualitySelect.value
            : "720";


    // ======================================
    // URL CHECK
    // ======================================

    if (!sourceUrl) {

        showMessage(
            "Please check a video URL first."
        );

        return;
    }


    // ======================================
    // QUALITY CHECK
    // ======================================

    const allowedQualities = [
        "720",
        "480",
        "360"
    ];


    const selectedQuality =
        allowedQualities.includes(quality)
            ? quality
            : "720";


    // ======================================
    // LOADING START
    // ======================================

    downloadVideoBtn.disabled = true;

    downloadVideoBtn.classList.add("loading");

    downloadVideoBtn.textContent =
        "Processing...";


    showMessage(
        `Preparing ${selectedQuality}p download...`
    );


    // ======================================
    // API REQUEST
    // ======================================

    try {

        const response = await fetch(
            "/api/download",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({

                    url: sourceUrl,

                    quality: selectedQuality

                })

            }
        );


        let data = {};

        try {
            data = await response.json();
        }

        catch (jsonError) {
            data = {};
        }


        // ==================================
        // SUCCESS
        // ==================================

        if (
            response.ok &&
            data.success
        ) {

            showMessage(
                "✓ Download is ready."
            );


            if (data.download_url) {

                window.location.href =
                    data.download_url;

            }

            else {

                showMessage(
                    "✕ Download link was not received."
                );

            }

        }


        // ==================================
        // ERROR
        // ==================================

        else {

            showMessage(
                "✕ " +
                (
                    data.message ||
                    "Download failed."
                )
            );

        }

    }


    // ======================================
    // NETWORK ERROR
    // ======================================

    catch (error) {

        console.error(error);

        showMessage(
            "Download failed. Please try again."
        );

    }


    // ======================================
    // LOADING END
    // ======================================

    finally {

        downloadVideoBtn.disabled = false;

        downloadVideoBtn.classList.remove(
            "loading"
        );

        downloadVideoBtn.textContent =
            "Download Video";

    }

}