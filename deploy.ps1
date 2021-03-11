$remotePath = "~/dev/bililive-danmuku-record/";
$composeFilePath = "~/dev/"
$fileList = "main.py", # main
            "blivedm.py"
            "requirements.txt", # pip
            "dockerfile", # docker
            "docker-compose.yml";
foreach ($item in $fileList) {
    scp -r $item server2:$remotePath;
}
# ssh server ("cd {0};docker-compose down --rmi local;docker-compose up -d" -f $remotePath)
ssh server2 ("cd {0}; docker-compose up --build -d danmaku-record" -f $composeFilePath)