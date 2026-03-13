#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ScenarioLoader.generated.h"

USTRUCT(BlueprintType)
struct FScenarioPose
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadWrite)
    float X = 0.0f;

    UPROPERTY(BlueprintReadWrite)
    float Y = 0.0f;

    UPROPERTY(BlueprintReadWrite)
    float Z = 0.0f;
};

USTRUCT(BlueprintType)
struct FScenarioConfig
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadWrite)
    FString ScenarioId;

    UPROPERTY(BlueprintReadWrite)
    FString ObjectName;

    UPROPERTY(BlueprintReadWrite)
    FScenarioPose StartPose;

    UPROPERTY(BlueprintReadWrite)
    FScenarioPose TargetPose;

    UPROPERTY(BlueprintReadWrite)
    float PlacementToleranceMM = 20.0f;

    UPROPERTY(BlueprintReadWrite)
    float MaxCycleTimeSeconds = 6.0f;
};

UCLASS()
class OPS1_API AScenarioLoader : public AActor
{
    GENERATED_BODY()

public:
    AScenarioLoader();

    // Call this from Blueprint to load a scenario JSON file
    UFUNCTION(BlueprintCallable, Category = "OptiSim")
    bool LoadScenario(const FString& FilePath, FScenarioConfig& OutConfig);

    // Apply the loaded config to the level
    UFUNCTION(BlueprintCallable, Category = "OptiSim")
    bool ApplyScenario(const FScenarioConfig& Config);

protected:
    virtual void BeginPlay() override;
};